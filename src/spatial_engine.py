"""Rebuild local evidence: python src/spatial_engine.py (safe from any directory)."""
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]


def build():
    boundaries = gpd.read_file(ROOT / 'nga_lga_boundaries.geojson').to_crs(4326)
    if boundaries.shapeID.duplicated().any():
        raise ValueError('Boundary identifiers must be unique')
    with sqlite3.connect(ROOT / 'Nigeria Ookla.gpkg') as conn:
        tiles = pd.read_sql_query('SELECT fid, tile_x, tile_y, avg_d_kbps, avg_u_kbps, avg_lat_ms, tests FROM "Nigeria Ookla"', conn)
    tiles['mean_d_mbps'] = tiles.avg_d_kbps / 1000
    tiles['mean_u_mbps'] = tiles.avg_u_kbps / 1000
    tiles['mean_lat_ms'] = tiles.avg_lat_ms
    points = gpd.GeoDataFrame(tiles, geometry=gpd.points_from_xy(tiles.tile_x, tiles.tile_y), crs=4326)
    joined = gpd.sjoin(points, boundaries[['shapeID', 'geometry']], how='inner', predicate='intersects')
    multiple_matches = int((joined.groupby('fid').size() > 1).sum())
    joined = joined.sort_values('shapeID').drop_duplicates('fid')
    audit = {'schema_version': 1, 'observation_period': 'Not supplied with local extract', 'network_type': 'Unverified', 'ookla': {'source_rows': len(tiles), 'matched_rows': len(joined), 'unmatched_rows': len(tiles)-len(joined)}}
    stats = joined.groupby('shapeID').agg(tiles_count=('fid', 'size'), mean_d_mbps=('mean_d_mbps', 'mean'), mean_u_mbps=('mean_u_mbps', 'mean'), mean_lat_ms=('mean_lat_ms', 'mean'), total_tests=('tests', 'sum'))
    result = boundaries.merge(stats, on='shapeID', how='left')
    # Assign administrative context by largest polygon overlap, never by name alone.
    states = gpd.read_file(ROOT / 'nga_state_boundaries.geojson').to_crs(6933)
    projected = boundaries.to_crs(6933)
    state_matches = []
    for _, area in projected.iterrows():
        candidates = states.iloc[list(states.sindex.query(area.geometry, predicate='intersects'))]
        overlaps = candidates.geometry.intersection(area.geometry).area
        best = overlaps.idxmax() if len(overlaps) else None
        fraction = float(overlaps.loc[best] / area.geometry.area) if best is not None else 0
        state_matches.append({'shapeID': area.shapeID, 'state_name': states.loc[best, 'shapeName'] if best is not None else 'Unmatched', 'state_overlap_pct': round(100*fraction, 2), 'state_match_status': 'Matched by area overlap' if fraction >= .95 else 'Review boundary overlap'})
    result = result.merge(pd.DataFrame(state_matches), on='shapeID', how='left', validate='one_to_one')
    audit['matching'] = {'tile_method': 'Tile coordinate intersects LGA polygon; multiple candidates resolved by sorted shapeID', 'tiles_with_multiple_candidates': multiple_matches, 'state_method': 'Largest polygon intersection area in EPSG:6933; below 95% flagged for review', 'state_review_count': int((result.state_match_status != 'Matched by area overlap').sum())}

    result['tiles_count'] = result.tiles_count.fillna(0).astype(int)
    for filename, column in [('grid3_nga_health_facilities_v3_0.gpkg', 'health_facilities_count'), ('hotosm_nga_education_facilities_osm_gpkg/education_facilities.gpkg', 'schools_count')]:
        path = ROOT / filename
        result[column] = np.nan
        if path.exists():
            facilities = gpd.read_file(path).to_crs(4326)
            facilities = facilities[facilities.geometry.notna() & ~facilities.geometry.is_empty].copy()
            facilities.geometry = facilities.geometry.representative_point()
            facilities['_site'] = np.arange(len(facilities))
            matched = gpd.sjoin(facilities[['_site', 'geometry']], boundaries[['shapeID', 'geometry']], predicate='intersects')
            matched = matched.sort_values('shapeID').drop_duplicates('_site')
            result[column] = result.shapeID.map(matched.groupby('shapeID').size()).fillna(0).astype(int)
            audit[column] = {'valid_geometry_rows': len(facilities), 'matched_rows': len(matched), 'unmatched_rows': len(facilities)-len(matched), 'source': filename}
    def xyz(lon, lat):
        lon, lat = np.radians(lon), np.radians(lat)
        return np.column_stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
    good = tiles[(tiles.mean_u_mbps >= 2.5) & (tiles.mean_lat_ms < 80)]
    result['straight_line_km'] = np.nan
    if not good.empty:
        origin = result.geometry.representative_point()
        chord, _ = cKDTree(xyz(good.tile_x, good.tile_y)).query(xyz(origin.x, origin.y))
        result['straight_line_km'] = np.round(2 * 6371.0088 * np.arcsin(np.clip(chord/2, 0, 1)), 1)
    result['observation_period'] = 'Not supplied with local extract'
    result['network_type'] = 'Not verified from local extract'
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    result.to_file(out / 'sentinel_evidence.geojson', driver='GeoJSON')
    display = result[['shapeID', 'geometry']].copy()
    display.geometry = display.geometry.simplify(.008, preserve_topology=True)
    (out / 'sentinel_boundaries.json').write_text(display.to_json(), encoding='utf-8')
    result.drop(columns='geometry').to_csv(out / 'sentinel_evidence.csv', index=False)
    (out / 'sentinel_sources.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(f'Built {len(result)} LGAs; {(result.tiles_count == 0).sum()} without observations.')


if __name__ == '__main__':
    build()
