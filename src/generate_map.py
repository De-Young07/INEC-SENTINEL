import os
import json
import folium
from folium import plugins
import geopandas as gpd

print("Generating Interactive Leaflet Map matching reference layout...")

lga_path = "data/nigeria_lga_electoral_audit.geojson"
tiles_path = "data/nigeria_ookla_transmission_tiles.geojson"
state_path = "nga_state_boundaries.geojson"

gdf_lga = gpd.read_file(lga_path)
gdf_tiles = gpd.read_file(tiles_path)
gdf_state = gpd.read_file(state_path)

gdf_lga = gdf_lga.to_crs("EPSG:4326")
gdf_tiles = gdf_tiles.to_crs("EPSG:4326")
gdf_state = gdf_state.to_crs("EPSG:4326")

# Center of Nigeria: lat 9.0820, lon 8.6753
m = folium.Map(
    location=[9.0820, 8.6753],
    zoom_start=6,
    tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    control_scale=True
)

# 1. Add LGA Choropleth Layer
def style_lga(feature):
    score = feature['properties'].get('electoral_risk_score', 0)
    if score >= 70:
        fill = "#DC2626" # Crimson
        fill_opacity = 0.55
    elif score >= 45:
        fill = "#F59E0B" # Amber
        fill_opacity = 0.45
    else:
        fill = "#10B981" # Emerald Green
        fill_opacity = 0.35
    
    return {
        'fillColor': fill,
        'color': '#475569',
        'weight': 0.8,
        'fillOpacity': fill_opacity
    }

def highlight_lga(feature):
    return {
        'weight': 2.5,
        'color': '#0F172A',
        'fillOpacity': 0.8
    }

fg_lga = folium.FeatureGroup(name="Electoral Transmission Risk (774 LGAs)", show=True)

folium.GeoJson(
    gdf_lga,
    style_function=style_lga,
    highlight_function=highlight_lga,
    tooltip=folium.GeoJsonTooltip(
        fields=['shapeName', 'risk_category', 'electoral_risk_score', 'mean_u_mbps', 'transmission_travel_dist_km', 'tiles_count'],
        aliases=['LGA:', 'Transmission Risk:', 'Risk Score (0-100):', 'Avg Upload Speed:', 'Travel to Network:', 'Speed Test Tiles:'],
        localize=True,
        sticky=False,
        labels=True,
        style="background-color: #0F172A; color: #FFFFFF; font-family: Calibri, sans-serif; font-size: 12px; padding: 10px; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"
    ),
    popup=folium.GeoJsonPopup(
        fields=['shapeName', 'risk_category', 'electoral_risk_score', 'mean_d_mbps', 'mean_u_mbps', 'pct_blackout', 'transmission_travel_dist_km'],
        aliases=['Local Government Area:', 'Transmission Assessment:', 'Vulnerability Index:', 'Avg Download (Mbps):', 'Avg Upload (Mbps):', 'Blackout Tiles (%):', 'Min Travel Distance (km):'],
        localize=True,
        labels=True,
        style="font-family: Calibri; font-size: 13px;"
    )
).add_to(fg_lga)
fg_lga.add_to(m)

# 2. Add Ookla Speed Tiles (Micro Grid Cells)
fg_tiles = folium.FeatureGroup(name="Ookla Performance Micro-Tiles (Grid Cells)", show=False)

sample_tiles = gdf_tiles.sample(min(2500, len(gdf_tiles)), random_state=42)
for _, r in sample_tiles.iterrows():
    folium.CircleMarker(
        location=[r['tile_y'], r['tile_x']],
        radius=3,
        color=r['color'],
        fill=True,
        fill_color=r['color'],
        fill_opacity=0.75,
        tooltip=f"Tier: {r['transmission_tier']} | Upload: {r['avg_u_mbps']:.2f} Mbps | Lat: {r['avg_lat_ms']}ms"
    ).add_to(fg_tiles)
fg_tiles.add_to(m)

# 3. Add State Outlines
fg_state = folium.FeatureGroup(name="State Boundaries (36 States + FCT)", show=True)
folium.GeoJson(
    gdf_state,
    style_function=lambda f: {
        'fillColor': 'transparent',
        'color': '#0F172A',
        'weight': 1.8,
        'dashArray': '3, 3'
    },
    tooltip=folium.GeoJsonTooltip(fields=['shapeName'], aliases=['State:'])
).add_to(fg_state)
fg_state.add_to(m)

# 4. Add Critical Electoral Deserts Layer
fg_critical = folium.FeatureGroup(name="Critical Transmission Deserts (Priority Focus)", show=False)
gdf_critical = gdf_lga[gdf_lga['electoral_risk_score'] >= 70]
folium.GeoJson(
    gdf_critical,
    style_function=lambda f: {
        'fillColor': '#991B1B',
        'color': '#7F1D1D',
        'weight': 1.5,
        'fillOpacity': 0.75
    },
    tooltip=folium.GeoJsonTooltip(fields=['shapeName', 'electoral_risk_score'], aliases=['High-Risk LGA:', 'Risk Score:'])
).add_to(fg_critical)
fg_critical.add_to(m)

# 5. Layer Controls
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# 6. Floating Header Card & Legend matching reference screenshot
custom_html = """
<div id="floating-header" style="
    position: fixed;
    top: 15px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    background: rgba(255, 255, 255, 0.95);
    padding: 12px 28px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.18);
    border: 1px solid #cbd5e1;
    text-align: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    pointer-events: auto;
">
    <div style="font-size: 18px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;">
        INEC BVAS & IReV Transmission Feasibility Audit
    </div>
    <div style="font-size: 13px; font-weight: 500; color: #334155; margin-top: 2px;">
        A Spatial Telecommunications Assessment of Electronic Results Transmission Across Nigeria
    </div>
    <div style="font-size: 11px; color: #64748b; margin-top: 2px; font-style: italic;">
        National Infrastructure Assessment & Vulnerability Mapping • 774 Local Government Areas
    </div>
</div>

<div id="floating-legend" style="
    position: fixed;
    bottom: 25px;
    left: 20px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.95);
    padding: 14px 18px;
    border-radius: 8px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.18);
    border: 1px solid #cbd5e1;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    width: 270px;
">
    <div style="font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">
        Transmission Risk Legend
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 6px;">
        <span style="width: 14px; height: 14px; background: #dc2626; display: inline-block; margin-right: 9px; border-radius: 3px; flex-shrink: 0;"></span>
        <span style="font-size: 11.5px; color: #1e293b; font-weight: 600;">Critical Risk (Blackout / Travel > 10km)</span>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 6px;">
        <span style="width: 14px; height: 14px; background: #f59e0b; display: inline-block; margin-right: 9px; border-radius: 3px; flex-shrink: 0;"></span>
        <span style="font-size: 11.5px; color: #1e293b; font-weight: 600;">Moderate Risk (Degraded / Roaming)</span>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 6px;">
        <span style="width: 14px; height: 14px; background: #10b981; display: inline-block; margin-right: 9px; border-radius: 3px; flex-shrink: 0;"></span>
        <span style="font-size: 11.5px; color: #1e293b; font-weight: 600;">Low Risk (Optimal Real-Time Upload)</span>
    </div>
    <div style="border-top: 1px solid #e2e8f0; margin-top: 8px; padding-top: 6px; font-size: 10.5px; color: #64748b; line-height: 1.3;">
        <b>Audit Standard:</b> Form EC8A requires &ge; 1.0 Mbps upload throughput & &lt; 150ms latency for secure cloud transmission.
    </div>
</div>
"""
m.get_root().html.add_child(folium.Element(custom_html))

output_html = "interactive_electoral_map.html"
m.save(output_html)
print(f"Map generated and saved cleanly to {output_html}!")
