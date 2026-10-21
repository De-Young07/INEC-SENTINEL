"""SENTINEL web service. Run: python -m uvicorn src.web_api:app --port 8600."""
from functools import lru_cache
from pathlib import Path
import json
import os
import secrets
from typing import Literal
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from .readiness import screen, allocate_visits, Scenario, briefing
from . import monitoring

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title='SENTINEL', version='1.0.0')
app.add_middleware(GZipMiddleware, minimum_size=1000)


@lru_cache(maxsize=1)
def evidence():
    return screen(pd.read_csv(ROOT / 'data/sentinel_evidence.csv', dtype={'shapeID': str}))


class PlanRequest(BaseModel):
    budget: int = Field(default=5000000, ge=0, le=100000000000)
    cost_per_visit: int = Field(default=100000, gt=0, le=1000000000)
    max_visits: int = Field(default=20, ge=0, le=774)
    ids: list[str] | None = Field(default=None, max_length=774)


def prepare(request):
    df = evidence()
    if request.ids is not None:
        unknown = set(request.ids) - set(df.shapeID)
        if unknown:
            raise HTTPException(422, 'Unrecognized LGA identifier')
        df = df[df.shapeID.isin(request.ids)]
    scenario = Scenario(request.budget, request.cost_per_visit, request.max_visits)
    selected, summary = allocate_visits(df, scenario)
    return df, selected, scenario, summary


@app.get('/api/evidence')
def get_evidence():
    return json.loads(evidence().to_json(orient='records'))


@app.get('/api/boundaries')
@lru_cache(maxsize=1)
def boundaries():
    prepared = ROOT / 'data/sentinel_boundaries.json'
    if prepared.exists():
        return json.loads(prepared.read_text(encoding='utf-8'))
    # Display geometry only: analytical geometries remain untouched.
    import geopandas as gpd
    geo = gpd.read_file(ROOT / 'data/sentinel_evidence.geojson')[['shapeID', 'geometry']]
    geo.geometry = geo.geometry.simplify(.008, preserve_topology=True)
    return json.loads(geo.to_json())


@app.post('/api/plan')
def plan(request: PlanRequest):
    _, selected, _, summary = prepare(request)
    return {'summary': summary, 'selected': json.loads(selected.to_json(orient='records'))}


@app.post('/api/brief', response_class=HTMLResponse)
def brief(request: PlanRequest):
    df, selected, scenario, summary = prepare(request)
    return briefing(df, selected, scenario, summary)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'lgas': len(evidence())}


@lru_cache(maxsize=2)
def facility_data(version):
    return pd.read_csv(ROOT / 'data/facilities.csv', keep_default_na=False)


def facilities():
    path = ROOT / 'data/facilities.csv'
    if not path.exists():
        raise HTTPException(503, 'Build the register with python -m src.facilities')
    return facility_data(path.stat().st_mtime_ns)


@app.get('/api/facilities')
def list_facilities(q: str = Query('', max_length=100), source: str = '', lga: str = '', offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    frame = facilities()
    if q:
        frame = frame[frame['name'].str.contains(q, case=False, regex=False) | frame['site_id'].str.contains(q, case=False, regex=False)]
    if source:
        frame = frame[frame.source == source]
    if lga:
        frame = frame[frame.shapeID == lga]
    return {'total': len(frame), 'items': json.loads(frame.iloc[offset:offset+limit].to_json(orient='records'))}


@app.get('/api/sources')
def source_audit():
    return {name: json.loads((ROOT / 'data' / name).read_text(encoding='utf-8')) for name in ['sentinel_sources.json', 'facilities_audit.json'] if (ROOT / 'data' / name).exists()}


class Observation(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    site_id: str = Field(min_length=1, max_length=150)
    mode: Literal['demo', 'field'] = 'demo'
    observed_at: datetime
    success: bool
    seconds: float = Field(gt=0, le=3600, allow_inf_nan=False)
    carrier: str = Field(default='Unspecified', max_length=80)
    note: str = Field(default='', max_length=1000)


def authorized(token):
    expected = os.environ.get('SENTINEL_INGEST_TOKEN', '')
    return bool(expected) and secrets.compare_digest(token or '', expected)


def require_token(token):
    if not authorized(token):
        raise HTTPException(403, 'Enter the configured operator token to write monitoring records')


@app.get('/api/config')
def config():
    return {'hosted': bool(os.environ.get('VERCEL')), 'storage': 'postgres' if os.environ.get('DATABASE_URL') else 'sqlite'}


@app.post('/api/probe-upload')
async def probe_upload(request: Request, x_sentinel_token: str | None = Header(default=None)):
    require_token(x_sentinel_token)
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 262144:
            raise HTTPException(413, 'Synthetic upload limit is 256 KiB')
    if size == 0:
        raise HTTPException(422, 'Empty upload')
    return {'received_bytes': size, 'received_at': monitoring.now()}


@app.post('/api/observations')
def add_observation(body: Observation, x_sentinel_token: str | None = Header(default=None)):
    if body.mode == 'field' or os.environ.get('VERCEL'):
        require_token(x_sentinel_token)
    if body.site_id not in set(facilities().site_id):
        raise HTTPException(422, 'Choose a registered facility')
    payload = body.model_dump()
    payload['observed_at'] = body.observed_at.isoformat()
    try:
        return monitoring.record(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/monitoring')
def monitor(site_id: str | None = None, x_sentinel_token: str | None = Header(default=None)):
    return monitoring.snapshot(site_id, public_only=bool(os.environ.get('VERCEL')) and not authorized(x_sentinel_token))


class Acknowledgment(BaseModel):
    actor: str = Field(min_length=2, max_length=100)
    note: str = Field(min_length=3, max_length=1000)


@app.post('/api/incidents/{incident_id}/acknowledge')
def ack(incident_id: int, body: Acknowledgment, x_sentinel_token: str | None = Header(default=None)):
    if os.environ.get('VERCEL'):
        require_token(x_sentinel_token)
    with monitoring.connect() as db:
        row = db.execute('SELECT mode FROM incidents WHERE id=?', (incident_id,)).fetchone()
    if row and row['mode'] == 'field':
        require_token(x_sentinel_token)
    try:
        monitoring.acknowledge(incident_id, body.actor.strip(), body.note.strip())
        return {'ok': True}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


app.mount('/', StaticFiles(directory=ROOT / 'web', html=True), name='web')
