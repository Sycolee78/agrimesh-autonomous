"""
Farm Planner - Interactive Zimbabwe AEZ Map
Click anywhere in Zimbabwe to get farm recommendations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.allocators.aez_lookup import AEZLookupAgent
from src.allocators.pipeline import plan_farm, FarmPlan

st.set_page_config(
    page_title="Farm Planner - AgriMesh", 
    page_icon="🗺️", 
    layout="wide"
)

# Load AEZ data
@st.cache_resource
def load_aez_agent():
    return AEZLookupAgent()

@st.cache_data
def load_aez_geojson():
    geojson_path = Path(__file__).parent.parent.parent / "data" / "aez" / "zimbabwe_boundaries.geojson"
    with open(geojson_path) as f:
        return json.load(f)

@st.cache_data
def load_cities():
    geojson = load_aez_geojson()
    return geojson.get("provinces", [])

aez_agent = load_aez_agent()
aez_geojson = load_aez_geojson()
cities = load_cities()

# Zimbabwe bounds
ZW_BOUNDS = {
    "min_lat": -22.5,
    "max_lat": -15.5,
    "min_lon": 25.0,
    "max_lon": 33.0,
    "center_lat": -19.0,
    "center_lon": 29.0,
}

# Zone colors
ZONE_COLORS = {
    "I": "#1a9850",
    "II": "#91cf60", 
    "III": "#d9ef8b",
    "IV": "#fee08b",
    "V": "#d73027",
}

ZONE_DESCRIPTIONS = {
    "I": "Specialized & Diversified (>1000mm rain) - Tea, coffee, intensive dairy",
    "II": "Intensive Farming (750-1000mm) - Maize, tobacco, cotton",
    "III": "Semi-Intensive (650-800mm) - Mixed crop-livestock",
    "IV": "Semi-Extensive (450-650mm) - Livestock, drought-tolerant crops",
    "V": "Extensive (<500mm) - Cattle/game ranching only",
}


def create_zone_legend():
    """Create HTML legend for AEZ zones."""
    html = "<div style='background: white; padding: 10px; border-radius: 5px;'>"
    html += "<h4 style='margin: 0 0 10px 0;'>Agro-Ecological Zones</h4>"
    for zone, color in ZONE_COLORS.items():
        html += f"""
        <div style='display: flex; align-items: center; margin: 5px 0;'>
            <div style='width: 20px; height: 20px; background: {color}; margin-right: 8px; border-radius: 3px;'></div>
            <span><b>Zone {zone}:</b> {ZONE_DESCRIPTIONS[zone][:40]}...</span>
        </div>
        """
    html += "</div>"
    return html


def create_map_html(lat: Optional[float] = None, lon: Optional[float] = None):
    """Create Leaflet map with Zimbabwe AEZ zones."""
    selected_marker = ""
    if lat and lon:
        selected_marker = f"""
        L.marker([{lat}, {lon}], {{
            icon: L.divIcon({{
                className: 'selected-marker',
                html: '<div style="background: red; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }})
        }}).addTo(map).bindPopup('Selected Location<br>Lat: {lat:.4f}<br>Lon: {lon:.4f}').openPopup();
        """
    
    # Create GeoJSON for zones
    zone_features = [f for f in aez_geojson["features"] if f["properties"].get("zone")]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 100%; width: 100%; }}
            body {{ margin: 0; padding: 0; }}
            .leaflet-popup-content {{ min-width: 200px; }}
            .zone-label {{ 
                font-weight: bold; 
                font-size: 14px;
                text-shadow: 1px 1px 2px white;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([{ZW_BOUNDS['center_lat']}, {ZW_BOUNDS['center_lon']}], 6);
            
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);
            
            // Zone colors
            var zoneColors = {json.dumps(ZONE_COLORS)};
            
            // Add AEZ zones
            var zones = {json.dumps(zone_features)};
            
            zones.forEach(function(zone) {{
                var color = zoneColors[zone.properties.zone] || '#gray';
                var layer = L.geoJSON(zone, {{
                    style: {{
                        fillColor: color,
                        weight: 2,
                        opacity: 0.8,
                        color: 'white',
                        fillOpacity: 0.5
                    }}
                }}).addTo(map);
                
                layer.bindPopup(
                    '<b>Zone ' + zone.properties.zone + '</b><br>' +
                    zone.properties.name + '<br>' +
                    'Avg Rainfall: ' + (zone.properties.rainfall_mm || 'N/A') + ' mm'
                );
            }});
            
            // Add cities
            var cities = {json.dumps(cities)};
            cities.forEach(function(city) {{
                var marker = L.circleMarker([city.lat, city.lon], {{
                    radius: city.type === 'capital' ? 8 : 5,
                    fillColor: city.type === 'capital' ? '#ff0000' : '#333',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }}).addTo(map);
                marker.bindTooltip(city.name, {{permanent: false, direction: 'top'}});
            }});
            
            // Selected location marker
            {selected_marker}
            
            // Click handler
            map.on('click', function(e) {{
                var lat = e.latlng.lat.toFixed(6);
                var lng = e.latlng.lng.toFixed(6);
                
                // Check bounds
                if (lat < {ZW_BOUNDS['min_lat']} || lat > {ZW_BOUNDS['max_lat']} ||
                    lng < {ZW_BOUNDS['min_lon']} || lng > {ZW_BOUNDS['max_lon']}) {{
                    alert('Please select a location within Zimbabwe');
                    return;
                }}
                
                // Send to Streamlit
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: {{lat: parseFloat(lat), lon: parseFloat(lng)}}
                }}, '*');
                
                // Update URL for persistence
                var url = new URL(window.parent.location);
                url.searchParams.set('lat', lat);
                url.searchParams.set('lon', lng);
                window.parent.history.replaceState(null, '', url);
                
                // Reload parent to update
                window.parent.location.reload();
            }});
            
            // Add legend
            var legend = L.control({{position: 'bottomright'}});
            legend.onAdd = function(map) {{
                var div = L.DomUtil.create('div', 'legend');
                div.innerHTML = `{create_zone_legend()}`;
                return div;
            }};
            legend.addTo(map);
        </script>
    </body>
    </html>
    """
    return html


def display_aez_profile(profile: Dict[str, Any]):
    """Display AEZ profile in a nice format."""
    st.markdown(f"""
    ### 📍 Zone {profile['zone']} - {profile['zone_name']}
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Mean Rainfall", f"{profile['rainfall_mm']['mean']} mm")
        st.metric("Growing Season", f"{profile['growing_season_days']['min']}-{profile['growing_season_days']['max']} days")
    
    with col2:
        st.metric("Rainfall Reliability", f"{profile['rainfall_reliability']:.0%}")
        st.metric("Drought Risk", profile['drought_risk'].upper())
    
    with col3:
        st.metric("Elevation", f"{profile['elevation_m']['min']}-{profile['elevation_m']['max']} m")
        st.caption(f"Soil Types: {', '.join(profile['soil_types'][:2])}")


def display_allocation(allocation: Dict[str, Any]):
    """Display farm allocation results."""
    st.markdown("### 🌱 Recommended Allocation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Crops**")
        crops = allocation.get("allocation", {}).get("crops", {})
        for crop, area in crops.items():
            if area > 0.1:
                st.write(f"• {crop.title()}: **{area:.2f} ha**")
    
    with col2:
        st.markdown("**Livestock**")
        livestock = allocation.get("allocation", {}).get("livestock", {})
        for ls, count in livestock.items():
            if count > 0:
                st.write(f"• {ls.title()}: **{count} head**")


def display_economics(profit: Dict[str, Any], multi_year: Dict[str, Any]):
    """Display economic projections."""
    st.markdown("### 💰 Economic Projections")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Year 1 Profit", f"${profit['net_profit_usd']:,.0f}")
    
    with col2:
        st.metric("ROI", f"{profit['roi_percent']:.1f}%")
    
    with col3:
        st.metric("Profit/ha", f"${profit['profit_per_ha_usd']:,.0f}")
    
    with col4:
        expected = multi_year['summary']['expected_total_profit']
        st.metric("3-Year Total", f"${expected:,.0f}")
    
    # Scenario comparison
    st.markdown("**Scenario Analysis**")
    scenarios = multi_year.get('scenarios', {})
    
    df = pd.DataFrame([
        {"Scenario": "Pessimistic", "3-Year Profit": scenarios.get('pessimistic', {}).get('total_profit', 0)},
        {"Scenario": "Expected", "3-Year Profit": scenarios.get('expected', {}).get('total_profit', 0)},
        {"Scenario": "Optimistic", "3-Year Profit": scenarios.get('optimistic', {}).get('total_profit', 0)},
    ])
    
    st.bar_chart(df.set_index("Scenario"))


def display_resources(resources: Dict[str, Any]):
    """Display resource requirements."""
    st.markdown("### 🔧 Resource Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Water**")
        water = resources['water']
        st.write(f"• Total: **{water['total_requirement_m3_year']:,.0f} m³/year**")
        st.write(f"• Irrigation: {water['breakdown']['irrigation_m3']:,.0f} m³")
        st.write(f"• Livestock: {water['breakdown']['livestock_m3']:,.0f} m³")
        if water['deficit_m3'] > 0:
            st.warning(f"⚠️ Deficit: {water['deficit_m3']:,.0f} m³")
    
    with col2:
        st.markdown("**Labor**")
        labor = resources['labor']
        st.write(f"• Total: **{labor['total_labor_days_year']:,.0f} days/year**")
        st.write(f"• Peak month: {labor['seasonality']['peak_month']}")
        if labor['labor_needs']['hired_needed_days'] > 0:
            st.write(f"• Hired labor needed: {labor['labor_needs']['hired_needed_days']:.0f} days")


def display_recommendations(plan: FarmPlan):
    """Display recommendations and risks."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Key Recommendations")
        for rec in plan.key_recommendations:
            st.success(rec)
    
    with col2:
        st.markdown("### ⚠️ Risk Factors")
        for risk in plan.risk_factors:
            st.warning(risk)


# Main UI
st.title("🗺️ Zimbabwe Farm Planner")
st.markdown("""
Click anywhere on the map to select a location and get AI-powered farm recommendations 
based on Zimbabwe's Agro-Ecological Zones.
""")

# Get coordinates from URL params
query_params = st.query_params
selected_lat = float(query_params.get("lat", 0)) if "lat" in query_params else None
selected_lon = float(query_params.get("lon", 0)) if "lon" in query_params else None

# Sidebar for manual input and settings
with st.sidebar:
    st.header("📍 Location")
    
    # Quick select cities
    city_names = ["Custom"] + [c["name"] for c in cities]
    selected_city = st.selectbox("Quick select", city_names)
    
    if selected_city != "Custom":
        city = next(c for c in cities if c["name"] == selected_city)
        selected_lat = city["lat"]
        selected_lon = city["lon"]
    
    # Manual coordinate input
    manual_lat = st.number_input("Latitude", value=selected_lat or -17.83, min_value=-22.5, max_value=-15.5, format="%.4f")
    manual_lon = st.number_input("Longitude", value=selected_lon or 31.05, min_value=25.0, max_value=33.0, format="%.4f")
    
    if st.button("Use Coordinates"):
        selected_lat = manual_lat
        selected_lon = manual_lon
        st.query_params["lat"] = str(selected_lat)
        st.query_params["lon"] = str(selected_lon)
        st.rerun()
    
    st.divider()
    
    st.header("⚙️ Farm Settings")
    area_ha = st.slider("Farm Area (ha)", min_value=1.0, max_value=50.0, value=7.0, step=0.5)
    
    objective = st.selectbox(
        "Optimization Objective",
        ["maximize_profit", "food_security", "soil_building", "balanced"],
        format_func=lambda x: x.replace("_", " ").title()
    )
    
    labor_days = st.number_input("Available Labor (days/year)", value=1000, min_value=100, max_value=5000)
    
    allowed = st.multiselect(
        "Allowed Enterprises (optional)",
        ["maize", "sorghum", "groundnuts", "vegetables", "fodder", "sunflower", "cotton", 
         "goats", "poultry", "cattle", "pigs", "sheep"],
        default=[]
    )

# Display map
st.subheader("🌍 Zimbabwe Agro-Ecological Zones")
map_html = create_map_html(selected_lat, selected_lon)
st.components.v1.html(map_html, height=500)

st.caption("Click on the map to select a location, or use the sidebar for manual input.")

# If location selected, show analysis
if selected_lat and selected_lon:
    st.divider()
    st.subheader(f"📊 Farm Analysis for ({selected_lat:.4f}, {selected_lon:.4f})")
    
    try:
        # Get AEZ profile
        profile = aez_agent.lookup(selected_lat, selected_lon)
        display_aez_profile(profile.to_dict())
        
        st.divider()
        
        # Run optimization
        with st.spinner("🔄 Calculating optimal farm plan..."):
            constraints = {"max_labor_days_per_year": labor_days}
            
            plan = plan_farm(
                lat=selected_lat,
                lon=selected_lon,
                area_ha=area_ha,
                objective=objective,
                constraints=constraints,
                allowed_enterprises=allowed if allowed else None,
            )
        
        # Display results in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🌱 Allocation", "💰 Economics", "🔧 Resources", "📅 Schedule", "🤖 Agents"
        ])
        
        with tab1:
            display_allocation(plan.allocation)
            
            # Visual allocation pie chart
            crops = plan.allocation.get("allocation", {}).get("crops", {})
            if crops:
                crop_data = [(c, a) for c, a in crops.items() if a > 0.1]
                if crop_data:
                    df = pd.DataFrame(crop_data, columns=["Crop", "Area (ha)"])
                    st.bar_chart(df.set_index("Crop"))
        
        with tab2:
            display_economics(plan.profit_estimate, plan.multi_year_projection)
        
        with tab3:
            display_resources(plan.resource_plan)
            
            # Infrastructure needs
            infra = plan.resource_plan.get("infrastructure", {})
            if infra.get("items"):
                st.markdown("**Infrastructure Needed**")
                for item in infra["items"]:
                    st.write(f"• {item['name']}: ${item['cost']:,.0f} ({item['priority']})")
        
        with tab4:
            schedule = plan.farm_schedule
            st.markdown("### 📅 Farm Schedule")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Planting Windows**")
                for crop, window in schedule.get("key_dates", {}).get("planting", {}).items():
                    st.write(f"• {crop.title()}: {window}")
            
            with col2:
                st.markdown("**Harvest Windows**")
                for crop, window in schedule.get("key_dates", {}).get("harvest", {}).items():
                    st.write(f"• {crop.title()}: {window}")
            
            st.markdown("**Labor by Month**")
            monthly = schedule.get("monthly_plans", [])
            if monthly:
                df = pd.DataFrame([
                    {"Month": m["month"], "Labor Days": m["total_labor_days"]}
                    for m in monthly
                ])
                st.bar_chart(df.set_index("Month"))
        
        with tab5:
            deployment = plan.agent_deployment
            st.markdown("### 🤖 Agent Deployment")
            
            st.metric("Total Agents", deployment.get("summary", {}).get("total_agents", 0))
            st.metric("Coverage", f"{deployment.get('summary', {}).get('coverage_percent', 0):.0f}%")
            
            st.markdown("**Deployed Agents**")
            for agent in deployment.get("agents", []):
                with st.expander(f"{agent['agent_type']} ({agent['agent_id']})"):
                    st.write(f"Assigned to: {', '.join(agent['assigned_to'])}")
                    st.write(f"Priority: {agent['priority']}")
                    st.write(f"Schedule: {agent['schedule']}")
                    st.json(agent.get("config", {}))
        
        st.divider()
        display_recommendations(plan)
        
        # Download plan
        st.divider()
        st.download_button(
            "📥 Download Full Plan (JSON)",
            data=plan.to_json(),
            file_name=f"farm_plan_{selected_lat:.2f}_{selected_lon:.2f}.json",
            mime="application/json",
        )
        
    except ValueError as e:
        st.error(f"⚠️ {e}")
    except Exception as e:
        st.error(f"Error generating plan: {e}")
        st.exception(e)

else:
    # Show zone summary when no location selected
    st.divider()
    st.subheader("📊 AEZ Zone Summary")
    
    zones = aez_agent.get_all_zones()
    
    for zone_id, zone_data in zones.items():
        with st.expander(f"Zone {zone_id}: {zone_data['name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Rainfall:** {zone_data['rainfall_mm']['min']}-{zone_data['rainfall_mm']['max']} mm")
                st.write(f"**Reliability:** {zone_data['rainfall_reliability']:.0%}")
                st.write(f"**Growing season:** {zone_data['growing_season_days']['min']}-{zone_data['growing_season_days']['max']} days")
            
            with col2:
                st.write(f"**Area:** {zone_data['percent_country']:.1f}% of Zimbabwe")
                st.write(f"**Provinces:** {', '.join(zone_data['provinces'][:3])}")
            
            st.caption(zone_data['description'])
