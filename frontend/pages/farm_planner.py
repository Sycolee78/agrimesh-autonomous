"""
Farm Planner - Interactive Zimbabwe map for AEZ-based farm planning.
Click on the map to analyze land and get optimized farm recommendations.
"""

import streamlit as st
import json
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.allocators.api import AEZOptimizerAPI

# Page config
st.set_page_config(
    page_title="AgriMesh Farm Planner",
    page_icon="🗺️",
    layout="wide",
)

# Initialize API
@st.cache_resource
def get_api():
    return AEZOptimizerAPI()

api = get_api()

# Load AEZ boundaries
@st.cache_data
def load_boundaries():
    path = Path(__file__).parent.parent.parent / "data" / "aez" / "zimbabwe_boundaries.geojson"
    with open(path) as f:
        return json.load(f)

boundaries = load_boundaries()

# Title
st.title("🗺️ Zimbabwe Farm Planner")
st.markdown("""
**Click on the map to select a location**, then configure your farm parameters 
to get an optimized allocation plan based on Agro-Ecological Zone analysis.
""")

# Create columns for layout
col_map, col_config = st.columns([2, 1])

with col_config:
    st.subheader("📍 Location")
    
    # Location input (manual or from map click)
    input_method = st.radio("Input method:", ["Enter coordinates", "Select city/district"])
    
    if input_method == "Enter coordinates":
        col_lat, col_lon = st.columns(2)
        with col_lat:
            lat = st.number_input("Latitude", value=-17.83, min_value=-22.5, max_value=-15.5, step=0.01)
        with col_lon:
            lon = st.number_input("Longitude", value=31.05, min_value=25.0, max_value=33.0, step=0.01)
    else:
        cities = {
            "Harare": (-17.83, 31.05),
            "Bulawayo": (-20.13, 28.63),
            "Mutare": (-18.97, 32.67),
            "Gweru": (-19.45, 29.82),
            "Masvingo": (-20.07, 30.83),
            "Chinhoyi": (-17.36, 30.19),
            "Kwekwe": (-18.93, 29.81),
            "Kadoma": (-18.33, 29.92),
            "Chipinge": (-20.19, 32.62),
            "Bindura": (-17.30, 31.33),
            "Chegutu": (-18.13, 30.13),
            "Victoria Falls": (-17.93, 25.83),
            "Hwange": (-18.36, 26.50),
            "Beitbridge": (-22.22, 30.00),
            "Kariba": (-16.52, 28.80),
        }
        selected_city = st.selectbox("Select location:", list(cities.keys()))
        lat, lon = cities[selected_city]
        st.info(f"Coordinates: {lat:.2f}, {lon:.2f}")
    
    # Quick AEZ lookup
    try:
        aez_info = api.lookup_aez(lat, lon)
        zone_colors = {"I": "🟢", "II": "🟩", "III": "🟨", "IV": "🟧", "V": "🟥"}
        st.success(f"""
        **Zone {aez_info['zone']}** {zone_colors.get(aez_info['zone'], '')} 
        {aez_info['zone_name']}
        
        🌧️ Rainfall: {aez_info['rainfall_mm']['mean']}mm/year  
        ⚠️ Drought risk: {aez_info['drought_risk']}
        """)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    
    st.divider()
    st.subheader("🌾 Farm Configuration")
    
    area_ha = st.slider("Farm size (hectares)", min_value=1.0, max_value=100.0, value=7.0, step=0.5)
    
    objective = st.selectbox(
        "Optimization objective:",
        ["maximize_profit", "food_security", "soil_building"],
        format_func=lambda x: {
            "maximize_profit": "💰 Maximize Profit",
            "food_security": "🍽️ Food Security",
            "soil_building": "🌱 Soil Building",
        }[x]
    )
    
    st.subheader("🚜 Allowed Enterprises")
    
    col_crops, col_livestock = st.columns(2)
    
    with col_crops:
        st.markdown("**Crops:**")
        allow_maize = st.checkbox("Maize", value=True)
        allow_sorghum = st.checkbox("Sorghum", value=True)
        allow_groundnuts = st.checkbox("Groundnuts", value=True)
        allow_sunflower = st.checkbox("Sunflower", value=False)
        allow_vegetables = st.checkbox("Vegetables", value=True)
        allow_fodder = st.checkbox("Fodder", value=True)
    
    with col_livestock:
        st.markdown("**Livestock:**")
        allow_cattle = st.checkbox("Cattle", value=False)
        allow_goats = st.checkbox("Goats", value=True)
        allow_sheep = st.checkbox("Sheep", value=False)
        allow_poultry = st.checkbox("Poultry", value=True)
        allow_pigs = st.checkbox("Pigs", value=False)
    
    allowed = []
    if allow_maize: allowed.append("maize")
    if allow_sorghum: allowed.append("sorghum")
    if allow_groundnuts: allowed.append("groundnuts")
    if allow_sunflower: allowed.append("sunflower")
    if allow_vegetables: allowed.append("vegetables")
    if allow_fodder: allowed.append("fodder")
    if allow_cattle: allowed.append("cattle")
    if allow_goats: allowed.append("goats")
    if allow_sheep: allowed.append("sheep")
    if allow_poultry: allowed.append("poultry")
    if allow_pigs: allowed.append("pigs")
    
    st.divider()
    st.subheader("⚙️ Constraints")
    
    use_labor_limit = st.checkbox("Limit labor days")
    max_labor = None
    if use_labor_limit:
        max_labor = st.number_input("Max labor days/year", value=1000, min_value=100, max_value=5000)
    
    market_distance = st.slider("Distance to market (km)", min_value=1, max_value=100, value=20)
    
    # Run optimization button
    run_optimization = st.button("🚀 Generate Farm Plan", type="primary", use_container_width=True)

with col_map:
    st.subheader("🗺️ Zimbabwe AEZ Map")
    
    # Create map HTML with Leaflet
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 500px; width: 100%; }}
            .zone-label {{ 
                background: rgba(255,255,255,0.9); 
                padding: 2px 6px; 
                border-radius: 4px;
                font-weight: bold;
            }}
            .legend {{
                background: white;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);
            }}
            .legend h4 {{ margin: 0 0 5px; }}
            .legend-item {{ display: flex; align-items: center; margin: 3px 0; }}
            .legend-color {{ width: 20px; height: 14px; margin-right: 8px; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([{lat}, {lon}], 6);
            
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap'
            }}).addTo(map);
            
            // AEZ Zone colors
            var zoneColors = {{
                'I': '#1a9850',
                'II': '#91cf60', 
                'III': '#d9ef8b',
                'IV': '#fee08b',
                'V': '#d73027'
            }};
            
            // Add AEZ zones
            var geojsonData = {json.dumps(boundaries)};
            
            L.geoJSON(geojsonData, {{
                style: function(feature) {{
                    if (feature.properties.zone) {{
                        return {{
                            fillColor: feature.properties.color || zoneColors[feature.properties.zone],
                            weight: 2,
                            opacity: 1,
                            color: 'white',
                            fillOpacity: 0.5
                        }};
                    }}
                    return {{
                        weight: 2,
                        color: '#333',
                        fillOpacity: 0
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    if (feature.properties.zone) {{
                        layer.bindPopup(
                            '<b>Zone ' + feature.properties.zone + '</b><br>' +
                            feature.properties.name + '<br>' +
                            'Rainfall: ' + feature.properties.rainfall_mm + 'mm'
                        );
                    }}
                }}
            }}).addTo(map);
            
            // Add cities
            var cities = {json.dumps(boundaries.get('provinces', []))};
            cities.forEach(function(city) {{
                var icon = city.type === 'capital' ? '⭐' : '📍';
                L.marker([city.lat, city.lon], {{
                    icon: L.divIcon({{
                        className: 'city-marker',
                        html: '<span style="font-size:16px">' + icon + '</span>',
                        iconSize: [20, 20]
                    }})
                }}).addTo(map).bindPopup('<b>' + city.name + '</b>');
            }});
            
            // Selected location marker
            var selectedMarker = L.marker([{lat}, {lon}], {{
                icon: L.divIcon({{
                    className: 'selected-marker',
                    html: '<span style="font-size:24px">📍</span>',
                    iconSize: [30, 30]
                }})
            }}).addTo(map).bindPopup('<b>Selected Farm Location</b><br>Zone: ' + '{aez_info["zone"]}');
            
            // Add legend
            var legend = L.control({{position: 'bottomright'}});
            legend.onAdd = function(map) {{
                var div = L.DomUtil.create('div', 'legend');
                div.innerHTML = '<h4>AEZ Zones</h4>' +
                    '<div class="legend-item"><div class="legend-color" style="background:#1a9850"></div>I - Specialized</div>' +
                    '<div class="legend-item"><div class="legend-color" style="background:#91cf60"></div>II - Intensive</div>' +
                    '<div class="legend-item"><div class="legend-color" style="background:#d9ef8b"></div>III - Semi-Intensive</div>' +
                    '<div class="legend-item"><div class="legend-color" style="background:#fee08b"></div>IV - Semi-Extensive</div>' +
                    '<div class="legend-item"><div class="legend-color" style="background:#d73027"></div>V - Extensive</div>';
                return div;
            }};
            legend.addTo(map);
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(map_html, height=520)
    
    # Zone info cards
    st.subheader("📊 Zone Information")
    
    zone_cols = st.columns(5)
    zones = api.get_all_zones()
    
    for i, (zone_id, zone_data) in enumerate(zones.items()):
        with zone_cols[i]:
            is_current = zone_id == aez_info["zone"]
            border = "2px solid #1f77b4" if is_current else "1px solid #ddd"
            
            st.markdown(f"""
            <div style="border: {border}; border-radius: 8px; padding: 10px; text-align: center; background: {'#f0f7ff' if is_current else 'white'}">
                <h3 style="margin: 0; color: {'#1a9850' if zone_id == 'I' else '#91cf60' if zone_id == 'II' else '#d9ef8b' if zone_id == 'III' else '#fee08b' if zone_id == 'IV' else '#d73027'}">
                    Zone {zone_id}
                </h3>
                <p style="font-size: 12px; margin: 5px 0;">{zone_data['name'][:20]}...</p>
                <p style="margin: 0;"><b>{zone_data['rainfall_mm']['mean']}mm</b></p>
                <p style="font-size: 11px; color: #666;">{zone_data['percent_country']}% of country</p>
            </div>
            """, unsafe_allow_html=True)

# Run optimization
if run_optimization:
    with st.spinner("🔄 Optimizing farm allocation..."):
        constraints = {}
        if max_labor:
            constraints["max_labor_days_per_year"] = max_labor
        
        result = api.optimize({
            "location": {"lat": lat, "lon": lon},
            "area_ha": area_ha,
            "objective": objective,
            "constraints": constraints,
            "market_access": {"distance_km": market_distance},
            "allowed_enterprises": allowed,
        })
    
    st.divider()
    st.header("📋 Farm Plan Results")
    
    # Summary metrics
    summary = result.summary
    
    metric_cols = st.columns(5)
    with metric_cols[0]:
        st.metric("Zone", f"{summary['zone']} ({summary['zone_name'][:15]}...)")
    with metric_cols[1]:
        st.metric("Year 1 Profit", f"${summary['expected_profit_yr1']:,.0f}")
    with metric_cols[2]:
        st.metric("3-Year NPV", f"${summary['npv_3yr']:,.0f}")
    with metric_cols[3]:
        st.metric("Labor/Year", f"{summary['labor_days_year']:,.0f} days")
    with metric_cols[4]:
        st.metric("Capex Needed", f"${summary['capex_required']:,.0f}")
    
    # Allocation tabs
    tab_alloc, tab_schedule, tab_resources, tab_agents, tab_json = st.tabs([
        "🌾 Allocation", "📅 Schedule", "💧 Resources", "🤖 Agents", "📄 JSON"
    ])
    
    with tab_alloc:
        col_crops, col_livestock = st.columns(2)
        
        with col_crops:
            st.subheader("🌾 Crop Allocation")
            
            if result.allocation["crops"]:
                for crop in result.allocation["crops"]:
                    pct = (crop["ha"] / area_ha) * 100
                    st.markdown(f"""
                    **{crop['enterprise'].title()}**: {crop['ha']:.1f} ha ({pct:.0f}%)
                    """)
                    st.progress(pct / 100)
            else:
                st.info("No crops allocated")
        
        with col_livestock:
            st.subheader("🐐 Livestock")
            
            if result.allocation["livestock"]:
                for ls in result.allocation["livestock"]:
                    st.markdown(f"**{ls['type'].title()}**: {ls['count']} head")
            else:
                st.info("No livestock allocated")
        
        st.subheader("🔄 Rotation Plan")
        
        rot_cols = st.columns(len(result.rotation))
        for i, year in enumerate(result.rotation):
            with rot_cols[i]:
                st.markdown(f"**Year {year['year']}**")
                for crop, area in year["allocations"].items():
                    st.markdown(f"- {crop}: {area}")
                if year.get("notes"):
                    st.caption(year["notes"])
    
    with tab_schedule:
        st.subheader("📅 Annual Schedule")
        
        schedule = result.schedule
        
        st.metric("Peak Month", f"Month {schedule['peak_month']}", f"{schedule['peak_labor_days']} labor days")
        
        # Monthly breakdown
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        month_data = []
        for month_num, data in schedule["monthly_summary"].items():
            month_data.append({
                "Month": months[int(month_num) - 1],
                "Tasks": data["task_count"],
                "Labor Days": data["labor_days"],
                "Critical": data["critical_tasks"],
            })
        
        st.dataframe(month_data, use_container_width=True, hide_index=True)
    
    with tab_resources:
        st.subheader("💧 Water Requirements")
        water = result.resource_plan["water"]
        st.metric("Total Water/Year", f"{water['total_m3_year']:,.0f} m³")
        st.write(f"- Crop irrigation: {water['crop_irrigation_m3_year']:,.0f} m³")
        st.write(f"- Livestock: {water['livestock_drinking_m3_year']:,.0f} m³")
        st.write(f"- Recommended source: **{water['source_recommendation']}**")
        
        st.subheader("👷 Labor Requirements")
        labor = result.resource_plan["labor"]
        st.metric("Total Labor/Year", f"{labor['total_labor_days_year']:,.0f} days")
        st.write(f"- FTEs required: {labor['ftes_required']}")
        st.write(f"- Seasonal workers (peak): {labor['seasonal_workers_peak']}")
        
        st.subheader("🏗️ Infrastructure")
        infra = result.resource_plan["infrastructure"]
        st.metric("Total Capex", f"${infra['estimated_capex_usd']:,.0f}")
        for item in infra["items"]:
            st.write(f"- {item['item']}: ${item['cost_usd']:,.0f}")
    
    with tab_agents:
        st.subheader("🤖 Agent Deployment")
        
        agents = result.agents_plan["agents"]
        
        for agent in agents:
            with st.expander(f"**{agent['agent_type']}** (Priority: {agent['priority']})"):
                st.write(f"**ID:** {agent['agent_id']}")
                st.write(f"**Frequency:** {agent['schedule_frequency']}")
                st.write("**Responsibilities:**")
                for resp in agent["responsibilities"]:
                    st.write(f"  - {resp}")
                st.write(f"**Enterprises:** {', '.join(agent['assigned_enterprises'])}")
        
        st.subheader("📡 Alert Routing")
        for alert, agent in result.agents_plan["alert_routing"].items():
            st.write(f"- **{alert}** → {agent}")
    
    with tab_json:
        st.subheader("📄 Full JSON Output")
        st.json(result.to_dict())
        
        # Download button
        st.download_button(
            "📥 Download Plan (JSON)",
            result.to_json(),
            file_name=f"farm_plan_{lat}_{lon}_{area_ha}ha.json",
            mime="application/json",
        )

# Sidebar with AEZ reference
with st.sidebar:
    st.header("ℹ️ AEZ Reference")
    
    st.markdown("""
    **Zimbabwe Agro-Ecological Zones:**
    
    🟢 **Zone I** - Eastern Highlands
    - >1000mm rainfall
    - Tea, coffee, dairy
    
    🟩 **Zone II** - Intensive Farming
    - 750-1000mm rainfall  
    - Maize, tobacco, cotton
    
    🟨 **Zone III** - Semi-Intensive
    - 650-800mm rainfall
    - Livestock + drought-tolerant crops
    
    🟧 **Zone IV** - Semi-Extensive
    - 450-650mm rainfall
    - Ranching, sorghum, millet
    
    🟥 **Zone V** - Extensive
    - <500mm rainfall
    - Extensive ranching only
    """)
    
    st.divider()
    
    st.markdown("""
    **Optimization Objectives:**
    
    💰 **Maximize Profit**
    - Highest expected returns
    - May accept higher risk
    
    🍽️ **Food Security**
    - Prioritize staple crops
    - Lower risk tolerance
    
    🌱 **Soil Building**
    - Emphasize legumes
    - Long-term sustainability
    """)
