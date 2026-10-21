"""SENTINEL's Streamlit adapter. Analytical functions live in readiness.py."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timezone
import json
import pandas as pd
import pydeck as pdk
import streamlit as st
from readiness import Scenario, screen, allocate_visits, rehearsal_action, briefing
import monitoring
import uuid

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title='SENTINEL | Readiness planner', page_icon='🗺️', layout='wide')
st.markdown('''<style>
.stApp{background:#0B1220;color:#E8EFF7}
[data-testid="stMainBlockContainer"]{padding-top:2rem;max-width:1500px}
h1,h2,h3{color:#E8EFF7!important}
div[data-testid="stMetric"]{background:#152236;color:#E8EFF7;padding:18px;border-radius:8px;border:1px solid #294058}
div[data-testid="stMetric"] label,div[data-testid="stMetricValue"]{color:#E8EFF7!important}
[data-testid="stMetricValue"]{font-size:clamp(1.15rem,2vw,1.8rem)!important}
[data-testid="stMetricLabel"] p{white-space:normal!important;overflow:visible!important}
[data-testid="stAlert"]{background:#152B43;color:#D8E8F7}
[data-testid="stAlert"] p{color:#D8E8F7!important}
[data-testid="stCaptionContainer"]{color:#B8C8D9!important}
[data-testid="stSidebar"]{background:#101C2D}
button[data-baseweb="tab"]{font-size:15px;padding:12px 16px}
button[data-baseweb="tab"][aria-selected="true"]{color:#5DE1D4;font-weight:700}
p,li{line-height:1.6}
</style>''', unsafe_allow_html=True)


@st.cache_data
def load_evidence(version):
    df = pd.read_csv(ROOT / 'data/sentinel_evidence.csv', dtype={'shapeID': str})
    geo = json.loads((ROOT / 'data/sentinel_evidence.geojson').read_text(encoding='utf-8'))
    return df, geo


def display_table(df):
    return df[['shapeName', 'evidence_status', 'sample_strength', 'verification_priority', 'next_action']].rename(columns={'shapeName': 'Local government area', 'evidence_status': 'What we know', 'sample_strength': 'Evidence sample', 'verification_priority': 'Visit priority / 100', 'next_action': 'Suggested next step'})


st.title('SENTINEL')
st.markdown('### Connectivity readiness planner')
st.write('Find gaps in the evidence, plan verification visits, and share a clear decision brief.')
st.info('Planning prototype · Historical observations, not live network status. Schools are community facilities, not verified polling units.')
path = ROOT / 'data/sentinel_evidence.csv'
if not path.exists():
    st.warning('The evidence package has not been prepared. Ask the project maintainer to run the data setup in the README.')
    st.stop()
try:
    evidence, geometry = load_evidence((path.stat().st_mtime_ns, (ROOT / 'data/sentinel_evidence.geojson').stat().st_mtime_ns))
except (ValueError, OSError) as exc:
    st.error('The evidence package could not be opened. Please ask the project maintainer to rebuild it.')
    st.stop()

st.sidebar.header('Find your area')
query = st.sidebar.text_input('Find an LGA', placeholder='Type part of a name')
all_statuses = ['Insufficient evidence', 'Poor observed performance', 'Review performance', 'Lower observed concern']
statuses = st.sidebar.multiselect('Evidence to include', all_statuses, default=all_statuses)
ranked = screen(evidence)
scope = ranked[ranked.evidence_status.isin(statuses) & ranked.shapeName.str.contains(query, case=False, regex=False, na=False)].copy()
st.sidebar.caption('These filters apply to the map, visit plan and downloads.')
st.sidebar.markdown('**How to use this planner**\n\n1. Review the evidence.\n2. Choose a visit budget.\n3. Download your brief.')
metrics = st.columns(3)
metrics[0].metric('LGAs in your view', len(scope))
metrics[1].metric('Need first observations', int((scope.evidence_status == 'Insufficient evidence').sum()))
metrics[2].metric('Poor observed performance', int((scope.evidence_status == 'Poor observed performance').sum()))
if scope.empty:
    st.warning('No areas match your filters. Clear the name search or include another evidence category.')
    st.stop()

overview, plan, rehearsal, sources, operations = st.tabs(['1 · Evidence map', '2 · Visit budget & briefing', '3 · Demo observation', 'About the data', 'Facilities & alerts'])
with overview:
    st.subheader('Review connectivity evidence')
    st.write('Explore the map, then choose an LGA below to see its evidence. When ready, open **2 · Visit budget & briefing** to plan your next checks.')
    st.caption('Grey: insufficient evidence · Red: poor observed performance · Amber: review performance · Teal: lower observed concern. Colours are screening categories, not election outcomes.')
    colors = {'Insufficient evidence': [130, 143, 158, 160], 'Poor observed performance': [190, 55, 55, 190], 'Review performance': [211, 151, 37, 170], 'Lower observed concern': [35, 133, 126, 150]}
    lookup = scope.set_index('shapeID').to_dict('index')
    features = []
    for feature in geometry['features']:
        key = str(feature['properties']['shapeID'])
        if key in lookup:
            record = lookup[key]
            features.append({'type': 'Feature', 'geometry': feature['geometry'], 'properties': {'name': record['shapeName'], 'status': record['evidence_status'], 'color': colors[record['evidence_status']]}})
    st.pydeck_chart(pdk.Deck(map_style=None, initial_view_state=pdk.ViewState(latitude=9.1, longitude=8.7, zoom=5), layers=[pdk.Layer('GeoJsonLayer', {'type': 'FeatureCollection', 'features': features}, get_fill_color='properties.color', get_line_color=[245, 247, 250], line_width_min_pixels=.5, pickable=True)], tooltip={'text': '{name}\n{status}'}), height=430)
    st.caption('If the map cannot load, use the evidence table below. It contains the same filtered areas.')
    chosen_id = st.selectbox('Inspect an LGA', scope.shapeID.tolist(), format_func=lambda key: f"{lookup[key]['shapeName']} · {key}")
    row = lookup[chosen_id]
    st.write(f"**{row['evidence_status']}** — {row['next_action']}.")
    a, b, c = st.columns(3)
    a.metric('Observed tiles', int(row['tiles_count']))
    b.metric('Mean upload', 'Unknown' if pd.isna(row['mean_u_mbps']) else f"{row['mean_u_mbps']:.2f} Mbps")
    c.metric('Screening score / 100', 'Not scored' if pd.isna(row['screening_score']) else f"{row['screening_score']:.1f}")
    st.caption(f"Sample: {row['sample_strength']}. Observation period: {row['observation_period']}.")
    facilities = []
    for column, label in [('schools_count', 'education records'), ('health_facilities_count', 'health-facility records')]:
        facilities.append(f"{int(row[column]):,} {label}" if pd.notna(row[column]) else f'{label}: unavailable')
    st.write('Community facilities: ' + ' · '.join(facilities))
    if pd.notna(row['straight_line_km']):
        st.caption(f"Straight-line proximity: {row['straight_line_km']:.1f} km from an LGA interior point to a historically good-performance tile. This is not road distance or a verified upload location.")
    st.dataframe(display_table(scope), hide_index=True, width='stretch')
    st.download_button('Download evidence table', scope.to_csv(index=False), 'sentinel-evidence.csv', 'text/csv')

with plan:
    st.subheader('Make a practical verification shortlist')
    st.write('This plan funds one initial visit per selected LGA. It does not buy infrastructure or predict improved connectivity.')
    x, y, z = st.columns(3)
    budget = x.number_input('Total budget (₦)', min_value=0, value=5000000, step=100000)
    cost = y.number_input('Estimated cost per visit (₦)', min_value=1, value=100000, step=10000, help='Include travel, staff time and testing. Replace this example with your own estimate.')
    limit = z.number_input('Maximum visits your team can make', min_value=0, max_value=10000, value=20)
    scenario = Scenario(int(budget), int(cost), int(limit))
    selected, summary = allocate_visits(scope, scenario)
    x, y, z = st.columns(3)
    x.metric('Proposed visits', summary['selected'])
    y.metric('Estimated spend', f"₦{summary['estimated_spend']:,}")
    z.metric('Budget left', f"₦{summary['unspent']:,}")
    st.caption(f"{summary['remaining_lgas']} LGAs remain outside this shortlist. No visits means no spending; adjust your budget or capacity to add visits.")
    st.dataframe(display_table(selected), hide_index=True, width='stretch')
    st.write('Unknown areas receive priority 75 to encourage investigation. Other areas are ranked by their screening score. This is a transparent planning rule, not an optimized travel route.')
    if st.button('Keep this plan for comparison'):
        st.session_state['comparison'] = {'assumptions': asdict(scenario), 'summary': summary.copy()}
    previous = st.session_state.get('comparison')
    if previous:
        st.write('**Compared with your saved plan**')
        st.caption(f"Saved budget: ₦{previous['assumptions']['budget']:,}; visit cost: ₦{previous['assumptions']['cost_per_visit']:,}; visit limit: {previous['assumptions']['max_visits']}.")
        st.metric('Change in proposed visits', summary['selected'], delta=summary['selected'] - previous['summary']['selected'])
        st.metric('Change in estimated spend', f"₦{summary['estimated_spend']:,}", delta=f"₦{summary['estimated_spend'] - previous['summary']['estimated_spend']:,}", delta_color='off')
    notes = st.session_state.get('rehearsals', [])
    st.download_button('Download decision brief', briefing(scope, selected, scenario, summary, notes), 'sentinel-decision-brief.html', 'text/html')
    st.caption('Open the downloaded brief in a browser, then choose Print → Save as PDF. Its light layout is designed for printing.')
    bundle = {'schema_version': 1, 'assumptions': asdict(scenario), 'summary': summary, 'selected_lga_ids': selected.shapeID.tolist(), 'scope_lga_ids': scope.shapeID.tolist(), 'rehearsals': notes}
    st.download_button('Download reusable scenario', json.dumps(bundle, indent=2), 'sentinel-scenario.json', 'application/json')

with rehearsal:
    st.subheader('See how a new observation changes the next step')
    st.warning('Synthetic demonstration only. These notes do not change the historical evidence or visit allocation. A single site test cannot establish readiness across an LGA.')
    with st.form('rehearsal'):
        site = st.text_input('Demonstration location', value='Example community centre')
        completed = st.checkbox('The synthetic file finished uploading', value=True)
        seconds = st.number_input('Time taken or time spent trying (seconds)', min_value=1.0, max_value=3600.0, value=30.0)
        submitted = st.form_submit_button('Show suggested next step')
    if submitted:
        action = rehearsal_action(completed, seconds)
        observation = {'kind': 'synthetic_demo', 'lga_id': chosen_id, 'location': site, 'completed': completed, 'seconds': seconds, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'suggested_action': action}
        st.session_state.setdefault('rehearsals', []).append(observation)
        st.success(action)
        st.caption('The 60-second target is an illustrative demonstration assumption, not an INEC requirement.')
        st.rerun()
    for note in st.session_state.get('rehearsals', [])[-5:]:
        st.write(f"**Demo · {note['location']}** — {note['suggested_action']}")
    st.caption('Notes stay in this browser session. Download the scenario or brief to keep them.')
    if st.button('Clear demonstration notes'):
        st.session_state['rehearsals'] = []
        st.rerun()

with sources:
    st.subheader('What the evidence can tell you')
    st.write('Sources: local Ookla performance extract, geoBoundaries LGA polygons, GRID3 health facilities and HOT OSM education facilities. Dataset dates, mobile/fixed provenance and current operating status have not been verified.')
    st.write('The screening score combines upload deficit (70%) and latency deficit (30%). Upload deficit runs from 2.5 Mbps to zero. Latency deficit runs from 50 to 250 ms. Categories start at scores 35 and 65. These are illustrative thresholds, not validated failure probabilities.')
    st.write('A larger sample means at least 10 observed tiles and 30 tests; it does not establish freshness or representativeness. Tile averages are unweighted. Missing measurements remain unknown. Schools are not a substitute for an authoritative polling-unit register.')
    st.write('Before deployment: choose actual operational sites, collect recent carrier-specific observations, verify power and access, and obtain realistic costs. Satellite and roaming benefits need this additional evidence.')
    audit_path = ROOT / 'data/sentinel_sources.json'
    if audit_path.exists():
        with st.expander('Data preparation record'):
            st.json(json.loads(audit_path.read_text(encoding='utf-8')))

with operations:
    st.subheader('Facility register and incident rehearsal')
    st.caption('Shared persistent monitoring history with the web app. Synthetic demonstrations never send messages.')
    st.link_button('Open the web monitoring workspace', 'http://localhost:8600/monitor.html')
    st.link_button('Open the full team guide', 'http://localhost:8600/guide.html')
    register_path = ROOT / 'data/facilities.csv'
    if register_path.exists():
        @st.cache_data
        def load_register(version):
            return pd.read_csv(register_path, keep_default_na=False)
        register = load_register(register_path.stat().st_mtime_ns)
        local = register[register.shapeID == chosen_id]
        name_query = st.text_input('Search facility names in this LGA')
        local = local[local['name'].str.contains(name_query, case=False, regex=False)]
        st.write(f'{len(local):,} source records. Overlapping sources are not unique-facility counts.')
        st.dataframe(local[['site_id','name','source','facility_type','possible_duplicate_of']].head(100), hide_index=True)
        if not local.empty:
            site_id = st.selectbox('Facility for incident rehearsal', local.site_id.head(100).tolist())
            success = st.checkbox('Demo upload completed', key='monitor-success')
            if st.button('Record one synthetic monitoring observation'):
                monitoring.record({'event_id': str(uuid.uuid4()), 'site_id': site_id, 'mode':'demo', 'observed_at':datetime.now(timezone.utc).isoformat(), 'success':success, 'seconds':12 if success else 60, 'carrier':'Synthetic demo', 'note':'Streamlit demonstration'})
                st.success('Recorded. Three failed tests open an incident; two successes record recovery.')
            snapshot = monitoring.snapshot(site_id)
            st.dataframe(pd.DataFrame(snapshot['observations']), hide_index=True)
            st.dataframe(pd.DataFrame(snapshot['incidents']), hide_index=True)
            active = [r for r in snapshot['incidents'] if r['mode']=='demo' and r['status']!='resolved']
            if active:
                with st.form('monitor-ack'):
                    actor = st.text_input('Responsible officer')
                    note = st.text_input('Action being taken')
                    if st.form_submit_button('Acknowledge incident'):
                        try:
                            monitoring.acknowledge(active[0]['id'], actor, note)
                            st.success('Acknowledgment saved. Refresh to see the updated status.')
                        except ValueError as exc:
                            st.error(str(exc))
            st.caption(snapshot['delivery'])
            st.dataframe(pd.DataFrame([r for r in snapshot['outbox'] if r['incident_id'] in {i['id'] for i in snapshot['incidents']}]), hide_index=True)
    else:
        st.info('Build the register first: python -m src.facilities')
