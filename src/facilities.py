"""Build a reproducible facility register. Run python -m src.facilities."""
from pathlib import Path
import json
import re
import sqlite3
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]


def build():
    boundaries = gpd.read_file(ROOT / 'nga_lga_boundaries.geojson').to_crs(4326)
    frames, audit = [], {}
    specs = [
        ('GRID3', 'grid3_nga_health_facilities_v3_0.gpkg', 'health', 'OBJECTID', 'facility_name'),
        ('HOT-health', 'hotosm_nga_health_facilities_osm_gpkg/health_facilities.gpkg', 'health', 'id', 'name'),
        ('HOT-education', 'hotosm_nga_education_facilities_osm_gpkg/education_facilities.gpkg', 'education', 'id', 'name'),
    ]
    for source, filename, kind, key, name in specs:
        data = gpd.read_file(ROOT / filename, engine='pyogrio', fid_as_index=True).to_crs(4326)
        valid = data.geometry.notna() & ~data.geometry.is_empty
        audit[source] = {'source_records': len(data), 'usable_geometry': int(valid.sum()), 'excluded_geometry': int((~valid).sum()), 'file': filename}
        data = data.loc[valid].copy()
        data.geometry = data.geometry.representative_point()
        identifiers = data.index.to_series()
        data['source_identifier'] = data.get('unique_id' if source == 'GRID3' else key, identifiers).astype(str)
        data['site_id'] = source + ':' + identifiers.fillna(data.index.to_series().astype(str)).astype(str)
        if data.site_id.duplicated().any():
            raise ValueError(f'Duplicate source identifiers in {source}')
        data['name'] = data[name].fillna('Unnamed facility').astype(str)
        data['source'], data['kind'] = source, kind
        data['latitude'], data['longitude'] = data.geometry.y, data.geometry.x
        data['facility_type'] = data.get('facility_type', data.get('amenity', pd.Series(index=data.index, dtype=str)))
        data['functional_status'] = data.get('functional', 'Not supplied')
        data['quality_flags'] = data.get('issues', 'Not supplied')
        data['registry_code'] = data.get('nhfr_facility_code', '')
        joined = gpd.sjoin(data, boundaries[['shapeID', 'shapeName', 'geometry']], how='left', predicate='intersects')
        joined = joined.sort_values('shapeID').drop_duplicates('site_id')
        columns = ['site_id', 'source_identifier', 'source', 'kind', 'name', 'latitude', 'longitude', 'shapeID', 'shapeName', 'facility_type', 'functional_status', 'quality_flags', 'registry_code']
        frames.append(pd.DataFrame(joined[columns]))
    register = pd.concat(frames, ignore_index=True).fillna('')
    register['possible_duplicate_of'] = ''
    # Conservative review candidates only: same normalized name within ~200 m.
    grid = register[register.source == 'GRID3']
    hot = register[register.source == 'HOT-health']
    def sphere(frame):
        lon, lat = np.radians(frame.longitude.astype(float)), np.radians(frame.latitude.astype(float))
        return np.column_stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
    tree = cKDTree(sphere(grid))
    normalize = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    for index, candidates in zip(hot.index, tree.query_ball_point(sphere(hot), 0.2 / 6371.0088)):
        name = normalize(register.at[index, 'name'])
        if name and name != 'unnamedfacility':
            for candidate in candidates:
                row = grid.iloc[candidate]
                if normalize(row['name']) == name:
                    register.at[index, 'possible_duplicate_of'] = row.site_id
                    break
    with sqlite3.connect(ROOT / 'Nigeria Ookla.gpkg') as db:
        tiles = pd.read_sql_query('SELECT tile_x AS longitude,tile_y AS latitude,avg_u_kbps,avg_lat_ms FROM "Nigeria Ookla"', db)
    chord, nearest = cKDTree(sphere(tiles)).query(sphere(register))
    register['nearest_tile_km'] = np.round(2*6371.0088*np.arcsin(np.clip(chord/2,0,1)), 2)
    register['nearest_tile_upload_mbps'] = tiles.iloc[nearest].avg_u_kbps.to_numpy()/1000
    register['nearest_tile_latency_ms'] = tiles.iloc[nearest].avg_lat_ms.to_numpy()
    # Nearby historical observation is context, not a measurement of this facility.
    audit['reconciliation'] = {'method': 'Exact normalized name within 200 m; candidates for review, not confirmed merges', 'candidates': int((register.possible_duplicate_of != '').sum()), 'records': len(register), 'observation_date': 'Unverified; file refresh does not establish site freshness'}
    temporary = ROOT / 'data/facilities.pending.csv'
    register.to_csv(temporary, index=False)
    temporary.replace(ROOT / 'data/facilities.csv')
    (ROOT / 'data/facilities_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    build()
