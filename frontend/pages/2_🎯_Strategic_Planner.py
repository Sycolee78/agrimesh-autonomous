"""
Strategic Farm Planner - Complete AEZ-Aware Farm Planning

Generates comprehensive farm plans with:
- Enterprise rankings (crops + livestock + CEA)
- Capital tier classification (A/B/C)
- Profit probability projections
- Spatial layout visualization
- Risk assessment
- Energy & sustainability planning
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.strategic_planner import StrategicFarmPlanner
from src.strategic_planner.geospatial_analyzer import ZIMBABWE_AEZ_ZONES, MARKET_CENTERS

st.set_page_config(
    page_title="Strategic Planner - AgriMesh",
    page_icon="🎯",
    layout="wide"
)

# Initialize planner
@st.cache_resource
def get_planner():
    return StrategicFarmPlanner()

planner = get_planner()

# Zone colors
ZONE_COLORS = {
    "I": "#1a9850",
    "IIa": "#66bd63",
    "IIb": "#a6d96a",
    "III": "#d9ef8b",
    "IV": "#fee08b",
    "V": "#d73027",
}

TIER_COLORS = {
    "A": "#2ecc71",
    "B": "#f39c12",
    "C": "#3498db",
}

TIER_ICONS = {
    "A": "🚀",
    "B": "⚖️",
    "C": "🌱",
}


def format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 1000000:
        return f"${value/1000000:.1f}M"
    elif value >= 1000:
        return f"${value/1000:.1f}K"
    else:
        return f"${value:.0f}"


def render_land_analysis(land: Dict[str, Any]):
    """Render land analysis section."""
    st.subheader("🌍 Land Analysis")
    
    coords = land.get("coordinates", {})
    st.caption(f"Coordinates: ({coords.get('lat', 0):.4f}, {coords.get('lon', 0):.4f})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        zone = land.get("aez_zone", "N/A")
        st.metric("AEZ Zone", zone)
        zone_color = ZONE_COLORS.get(zone, "#gray")
        st.markdown(f"""
        <div style="background:{zone_color}; padding:5px 10px; border-radius:5px; color:white; text-align:center;">
            Zone {zone}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("Land Class", land.get("classification", {}).get("land_class", "N/A").replace("_", " ").title())
    
    with col3:
        climate = land.get("climate", {})
        st.metric("Annual Rainfall", f"{climate.get('annual_rainfall_mm', 0)} mm")
    
    with col4:
        st.metric("Rainfall Reliability", f"{climate.get('rainfall_reliability', 0)*100:.0f}%")
    
    # Details in expander
    with st.expander("📊 Detailed Land Analysis"):
        tab1, tab2, tab3, tab4 = st.tabs(["Climate", "Soil", "Water", "Access"])
        
        with tab1:
            climate = land.get("climate", {})
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Growing Days:** {climate.get('growing_days', 0)}")
                temp = climate.get("temperature_range", [0, 0])
                st.write(f"**Temperature Range:** {temp[0]}°C - {temp[1]}°C")
            with col2:
                st.write(f"**Frost Risk:** {climate.get('frost_risk', 'N/A').title()}")
        
        with tab2:
            soil = land.get("soil", {})
            st.write(f"**Soil Type:** {soil.get('type', 'N/A').replace('_', ' ').title()}")
            st.write(f"**Fertility:** {soil.get('fertility', 'N/A').title()}")
            st.write(f"**Depth:** {soil.get('depth_cm', 0)} cm")
            st.write(f"**Drainage:** {soil.get('drainage', 'N/A').title()}")
        
        with tab3:
            water = land.get("water", {})
            st.write(f"**Water Source:** {water.get('source', 'N/A').replace('_', ' ').title()}")
            st.write(f"**Reliability:** {water.get('reliability', 'N/A').title()}")
            st.write(f"**Borehole Feasibility:** {water.get('borehole_feasibility', 'N/A').title()}")
            st.write(f"**Flood Risk:** {water.get('flood_risk', 'N/A').title()}")
        
        with tab4:
            access = land.get("access", {})
            st.write(f"**Market Distance:** {access.get('market_distance_km', 0)} km")
            st.write(f"**Road Quality:** {access.get('road_quality', 'N/A').replace('_', ' ').title()}")
            st.write(f"**Grid Electricity:** {'Yes ✅' if access.get('electricity_access') else 'No ❌'}")
    
    # Constraints and recommendations
    classification = land.get("classification", {})
    constraints = classification.get("constraints", [])
    systems = classification.get("recommended_systems", [])
    
    if constraints:
        st.warning(f"**Constraints:** {', '.join(constraints)}")
    
    if systems:
        st.info(f"**Recommended Systems:** {', '.join(s.replace('_', ' ').title() for s in systems[:5])}")


def render_enterprise_rankings(rankings: List[Dict]):
    """Render enterprise rankings."""
    st.subheader("📊 Enterprise Rankings")
    
    if not rankings:
        st.info("No enterprises ranked for this location.")
        return
    
    # Top 3 as metrics
    col1, col2, col3 = st.columns(3)
    for i, (col, rank) in enumerate(zip([col1, col2, col3], rankings[:3])):
        with col:
            icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            st.metric(
                f"{icon} #{i+1} {rank.get('name', 'N/A')}",
                f"Score: {rank.get('scores', {}).get('overall', 0):.1f}",
                f"Profit: {format_currency(rank.get('economics', {}).get('estimated_profit_per_ha', 0))}/ha"
            )
    
    # Full table in expander
    with st.expander("View All Rankings"):
        df = pd.DataFrame([
            {
                "Rank": i + 1,
                "Enterprise": r.get("name", ""),
                "Category": r.get("category", "").replace("_", " ").title(),
                "Suitability": r.get("scores", {}).get("suitability", 0),
                "Profit Score": r.get("scores", {}).get("profit_potential", 0),
                "Risk": r.get("scores", {}).get("risk", 0),
                "Overall": r.get("scores", {}).get("overall", 0),
                "Profit/ha": f"${r.get('economics', {}).get('estimated_profit_per_ha', 0):,.0f}",
                "Capital Req": f"${r.get('economics', {}).get('capital_required', 0):,.0f}",
            }
            for i, r in enumerate(rankings)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_capital_tiers(capital_classes: Dict[str, Any]):
    """Render capital tier classification."""
    st.subheader("💰 Capital Tier Plans")
    
    recommended = capital_classes.get("recommended_tier", "B")
    reason = capital_classes.get("recommendation_reason", "")
    
    st.success(f"**Recommended: Tier {recommended}** — {reason}")
    
    # Create tabs for each tier
    tab_a, tab_b, tab_c = st.tabs([
        f"{TIER_ICONS['A']} Tier A: High Capital",
        f"{TIER_ICONS['B']} Tier B: Moderate Capital",
        f"{TIER_ICONS['C']} Tier C: Low Capital",
    ])
    
    for tab, tier_key in [(tab_a, "A"), (tab_b, "B"), (tab_c, "C")]:
        with tab:
            tier = capital_classes.get(tier_key)
            if not tier:
                st.warning(f"Tier {tier_key} plan not available for this configuration.")
                continue
            
            is_recommended = tier_key == recommended
            if is_recommended:
                st.markdown(f"⭐ **Recommended Tier**")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Capital", format_currency(tier.get("capital", {}).get("total_required", 0)))
            with col2:
                st.metric("Annual Profit", format_currency(tier.get("returns", {}).get("annual_profit", 0)))
            with col3:
                st.metric("3-Year ROI", f"{tier.get('returns', {}).get('roi_3yr_pct', 0):.1f}%")
            with col4:
                st.metric("Profit Probability", f"{tier.get('returns', {}).get('profit_probability_3yr_pct', 0):.1f}%")
            
            # Enterprise mix
            st.markdown("**Enterprise Mix:**")
            enterprise_details = tier.get("enterprise_details", [])
            if enterprise_details:
                for e in enterprise_details:
                    unit = e.get("allocation_unit", "ha")
                    alloc = e.get("allocation", 0)
                    st.write(f"• {e.get('name', '')}: {alloc:.1f} {unit} (${e.get('capital_required', 0):,.0f})")
            
            # Risk and timing
            col1, col2 = st.columns(2)
            with col1:
                risk_level = tier.get("risk", {}).get("level", "unknown")
                risk_color = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(risk_level, "⚪")
                st.write(f"**Risk Level:** {risk_color} {risk_level.title()}")
                st.write(f"**Breakeven:** {tier.get('timing', {}).get('breakeven_months', 0)} months")
            
            with col2:
                infra = tier.get("infrastructure", {})
                required = infra.get("required", [])
                if required:
                    st.write("**Required Infrastructure:**")
                    for item in required[:4]:
                        st.write(f"  • {item}")


def render_spatial_layout(layout: Dict[str, Any]):
    """Render spatial layout visualization."""
    st.subheader("🗺️ Farm Layout")
    
    zones = layout.get("zones", [])
    if not zones:
        st.info("No layout generated.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Area", f"{layout.get('total_area_ha', 0):.1f} ha")
    with col2:
        st.metric("Utilized", f"{layout.get('utilized_area_ha', 0):.1f} ha")
    with col3:
        scores = layout.get("scores", {})
        st.metric("Biosecurity", f"{scores.get('biosecurity', 0):.0f}/100")
    with col4:
        st.metric("Water Efficiency", f"{scores.get('water_efficiency', 0):.0f}/100")
    
    # Visual layout using simple grid
    st.markdown("**Zone Layout (Schematic):**")
    
    # Create a simple visualization
    zone_data = []
    for z in zones:
        pos = z.get("position", {})
        zone_data.append({
            "Zone": z.get("name", "Unknown"),
            "Type": z.get("type", "").replace("_", " ").title(),
            "Area (ha)": z.get("area_ha", 0),
            "X": pos.get("x", 0),
            "Y": pos.get("y", 0),
        })
    
    if zone_data:
        df = pd.DataFrame(zone_data)
        
        # Simple scatter plot as layout
        import altair as alt
        
        chart = alt.Chart(df).mark_rect(
            opacity=0.7,
            stroke="white",
            strokeWidth=2
        ).encode(
            x=alt.X("X:Q", scale=alt.Scale(domain=[0, 100]), title="Farm Width (relative)"),
            y=alt.Y("Y:Q", scale=alt.Scale(domain=[0, 100]), title="Farm Length (relative)"),
            color=alt.Color("Type:N", legend=alt.Legend(title="Zone Type")),
            tooltip=["Zone", "Type", "Area (ha)"]
        ).properties(
            width=600,
            height=400,
            title="Farm Zone Layout"
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    # Zone list
    with st.expander("📋 Zone Details"):
        for z in zones:
            st.write(f"**{z.get('name', 'Unknown')}** ({z.get('type', '').replace('_', ' ')}) — {z.get('area_ha', 0):.2f} ha")
            notes = z.get("notes", [])
            if notes:
                for note in notes:
                    st.caption(f"  • {note}")
    
    # Design notes
    design_notes = layout.get("design_notes", [])
    if design_notes:
        st.markdown("**Design Notes:**")
        for note in design_notes:
            st.write(f"• {note}")


def render_profitability(profit: Dict[str, Any]):
    """Render profitability projections."""
    st.subheader("📈 Profitability Projections")
    
    if not profit.get("scenarios"):
        st.info("No profitability data available.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    capital = profit.get("capital", {})
    metrics = profit.get("key_metrics", {})
    prob = profit.get("probability", {})
    
    with col1:
        st.metric("Total Capital Required", format_currency(capital.get("total_required", 0)))
    with col2:
        st.metric("Breakeven", f"{metrics.get('breakeven_months', 0)} months")
    with col3:
        st.metric("3-Year IRR", f"{metrics.get('irr_3yr_pct', 0):.1f}%")
    with col4:
        st.metric("Profit Probability", f"{prob.get('profit_probability_3yr_pct', 0):.1f}%")
    
    # Scenario chart
    scenarios = profit.get("scenarios", {})
    
    chart_data = []
    for scenario_name in ["pessimistic", "expected", "optimistic"]:
        scenario = scenarios.get(scenario_name, [])
        for year_data in scenario:
            chart_data.append({
                "Year": year_data.get("year", 0),
                "Scenario": scenario_name.title(),
                "Cumulative Profit": year_data.get("cumulative_profit", 0),
            })
    
    if chart_data:
        df = pd.DataFrame(chart_data)
        
        import altair as alt
        
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y("Cumulative Profit:Q", title="Cumulative Profit (USD)"),
            color=alt.Color("Scenario:N", scale=alt.Scale(
                domain=["Pessimistic", "Expected", "Optimistic"],
                range=["#e74c3c", "#3498db", "#2ecc71"]
            )),
            strokeDash=alt.StrokeDash("Scenario:N")
        ).properties(
            width=600,
            height=300,
            title="5-Year Profit Projection by Scenario"
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    # Sensitivity analysis
    sensitivity = profit.get("sensitivity", {})
    if sensitivity:
        st.markdown("**Sensitivity Analysis:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Price +10%", f"{sensitivity.get('price_10pct_change', 0):+.1f}% profit")
        with col2:
            st.metric("Yield +10%", f"{sensitivity.get('yield_10pct_change', 0):+.1f}% profit")
        with col3:
            st.metric("Cost +10%", f"-{sensitivity.get('cost_10pct_change', 0):.1f}% profit")


def render_risk_assessment(risk: Dict[str, Any]):
    """Render risk assessment."""
    st.subheader("⚠️ Risk Assessment")
    
    overall = risk.get("overall", {})
    level = overall.get("level", "unknown")
    score = overall.get("score", 0)
    
    # Risk level indicator
    level_colors = {"low": "#2ecc71", "moderate": "#f39c12", "high": "#e74c3c"}
    level_color = level_colors.get(level, "#95a5a6")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"""
        <div style="background:{level_color}; padding:20px; border-radius:10px; text-align:center;">
            <h2 style="margin:0; color:white;">{score:.0f}/100</h2>
            <p style="margin:0; color:white;">{level.upper()} RISK</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Category breakdown
        categories = risk.get("category_scores", {})
        cat_data = [
            {"Category": "Climate", "Score": categories.get("climate", 0)},
            {"Category": "Market", "Score": categories.get("market", 0)},
            {"Category": "Operational", "Score": categories.get("operational", 0)},
            {"Category": "Financial", "Score": categories.get("financial", 0)},
        ]
        
        df = pd.DataFrame(cat_data)
        st.bar_chart(df.set_index("Category"))
    
    # Top risks
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Risks:**")
        for r in risk.get("top_risks", [])[:5]:
            severity_icon = {"low": "🟢", "moderate": "🟡", "high": "🔴", "critical": "⛔"}.get(r.get("severity", ""), "⚪")
            st.write(f"{severity_icon} {r.get('name', '')} ({r.get('probability', 0)*100:.0f}% prob)")
    
    with col2:
        st.markdown("**Recommended Mitigations:**")
        for m in risk.get("mitigations", [])[:5]:
            st.write(f"✅ {m}")
    
    # Scenario impacts
    st.markdown("**Scenario Impacts:**")
    impacts = risk.get("scenario_impacts", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Drought Impact", f"-{impacts.get('drought_impact_pct', 0):.0f}%")
    with col2:
        st.metric("Price Crash Impact", f"-{impacts.get('price_crash_impact_pct', 0):.0f}%")
    with col3:
        st.metric("Disease Outbreak", f"-{impacts.get('disease_outbreak_impact_pct', 0):.0f}%")


def render_energy_plan(energy: Dict[str, Any]):
    """Render energy and sustainability plan."""
    st.subheader("⚡ Energy & Sustainability")
    
    # Sustainability score
    scores = energy.get("scores", {})
    overall_score = scores.get("overall_sustainability", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sustainability Score", f"{overall_score:.0f}/100")
    with col2:
        st.metric("Energy Self-Sufficiency", f"{scores.get('energy_self_sufficiency', 0):.0f}%")
    with col3:
        st.metric("Water Self-Sufficiency", f"{scores.get('water_self_sufficiency', 0):.0f}%")
    with col4:
        st.metric("Circularity", f"{scores.get('circularity', 0):.0f}/100")
    
    st.info(f"**Recommended Model:** {energy.get('recommended_model', 'N/A')}")
    
    # Power system
    power = energy.get("power", {})
    solar = power.get("solar_system")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Power System:**")
        if solar:
            st.write(f"• Solar Capacity: {solar.get('capacity_kw', 0):.1f} kW")
            st.write(f"• Panels: {solar.get('panel_count', 0)}")
            st.write(f"• Battery: {solar.get('battery_kwh', 0):.0f} kWh")
            st.write(f"• Daily Generation: {solar.get('daily_generation_kwh', 0):.1f} kWh")
            st.write(f"• Cost: {format_currency(solar.get('cost_usd', 0))}")
            st.write(f"• Payback: {solar.get('payback_years', 0):.1f} years")
        else:
            st.write("Grid power recommended")
    
    with col2:
        st.markdown("**Water System:**")
        water = energy.get("water", {}).get("system", {})
        if water:
            if water.get("borehole_depth_m"):
                st.write(f"• Borehole: {water.get('borehole_depth_m', 0)}m depth")
                st.write(f"• Pump: {water.get('pump_type', 'N/A').replace('_', ' ')}")
            st.write(f"• Tank: {water.get('tank_capacity_liters', 0):,} L")
            st.write(f"• Rainwater Harvest: {water.get('rainwater_harvest_liters_year', 0):,} L/year")
            st.write(f"• Cost: {format_currency(water.get('cost_usd', 0))}")
    
    # Resource loops
    loops = energy.get("resource_loops", [])
    if loops:
        st.markdown("**Circular Resource Loops:**")
        for loop in loops:
            st.write(f"♻️ **{loop.get('name', '')}:** {loop.get('input', '')} → {loop.get('output', '')} (${loop.get('annual_value_usd', 0):,.0f}/year)")
    
    # Economics
    economics = energy.get("economics", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Infrastructure Cost", format_currency(economics.get("total_infrastructure_cost_usd", 0)))
    with col2:
        st.metric("Annual Savings", format_currency(economics.get("annual_savings_usd", 0)))
    with col3:
        st.metric("Carbon Offset", f"{economics.get('carbon_offset_tons_year', 0):.1f} t CO₂/year")


# Main UI
st.title("🎯 Strategic Farm Planner")
st.markdown("""
Generate comprehensive, AEZ-aware farm plans with enterprise rankings, 
profitability projections, spatial layouts, and sustainability planning.
""")

# Sidebar inputs
with st.sidebar:
    st.header("📍 Location & Area")
    
    # Quick select cities
    city_options = [{"name": "Custom", "lat": -17.83, "lon": 31.05}] + MARKET_CENTERS
    city_names = [c["name"] for c in city_options]
    selected_city = st.selectbox("Quick Select City", city_names)
    
    if selected_city != "Custom":
        city = next(c for c in city_options if c["name"] == selected_city)
        default_lat = city["lat"]
        default_lon = city["lon"]
    else:
        default_lat = -17.83
        default_lon = 31.05
    
    lat = st.number_input("Latitude", value=default_lat, min_value=-22.5, max_value=-15.5, format="%.4f")
    lon = st.number_input("Longitude", value=default_lon, min_value=25.0, max_value=33.0, format="%.4f")
    area_ha = st.slider("Farm Area (ha)", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
    
    st.divider()
    
    st.header("💰 Constraints")
    has_capital_limit = st.checkbox("Set Capital Limit")
    capital = None
    if has_capital_limit:
        capital = st.number_input("Available Capital (USD)", value=25000, min_value=1000, max_value=500000, step=1000)
    
    labor_days = st.number_input("Available Labor (days/year)", value=1000, min_value=100, max_value=5000)
    
    st.divider()
    
    st.header("🎛️ Preferences")
    preferred_tier = st.selectbox(
        "Preferred Capital Tier",
        ["Auto", "A - High Capital", "B - Moderate", "C - Low Capital"],
    )
    tier_map = {"Auto": None, "A - High Capital": "A", "B - Moderate": "B", "C - Low Capital": "C"}
    selected_tier = tier_map[preferred_tier]
    
    has_irrigation = st.checkbox("Has Existing Irrigation")
    has_electricity = st.checkbox("Has Grid Electricity")
    
    st.divider()
    
    generate = st.button("🚀 Generate Strategic Plan", type="primary", use_container_width=True)

# Main content
if generate:
    with st.spinner("🔄 Generating comprehensive farm plan..."):
        try:
            plan = planner.generate_plan(
                lat=lat,
                lon=lon,
                area_ha=area_ha,
                available_capital=capital,
                available_labor_days=labor_days,
                has_irrigation=has_irrigation,
                has_electricity=has_electricity,
                preferred_tier=selected_tier,
            )
            
            st.success("✅ Plan generated successfully!")
            
            # Store in session state
            st.session_state["strategic_plan"] = plan
            
        except Exception as e:
            st.error(f"Error generating plan: {e}")
            st.exception(e)
            plan = None

# Display plan if available
if "strategic_plan" in st.session_state:
    plan = st.session_state["strategic_plan"]
    
    # Summary card
    summary = plan.get("summary", {})
    
    st.markdown("---")
    
    # Quick summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("AEZ Zone", summary.get("aez_zone", "N/A"))
    with col2:
        st.metric("Recommended Tier", summary.get("recommended_tier", "N/A"))
    with col3:
        st.metric("Capital Required", format_currency(summary.get("capital_required_usd", 0)))
    with col4:
        st.metric("Annual Profit", format_currency(summary.get("expected_annual_profit_usd", 0)))
    with col5:
        st.metric("Profit Probability", f"{summary.get('profit_probability_pct', 0):.0f}%")
    
    st.markdown("---")
    
    # Tabs for different sections
    tabs = st.tabs([
        "🌍 Land Analysis",
        "📊 Enterprise Rankings",
        "💰 Capital Tiers",
        "🗺️ Spatial Layout",
        "📈 Profitability",
        "⚠️ Risk Assessment",
        "⚡ Sustainability",
        "📥 Export",
    ])
    
    with tabs[0]:
        render_land_analysis(plan.get("land_analysis", {}))
    
    with tabs[1]:
        render_enterprise_rankings(plan.get("enterprise_rankings", []))
    
    with tabs[2]:
        render_capital_tiers(plan.get("capital_classes", {}))
    
    with tabs[3]:
        render_spatial_layout(plan.get("recommended_layout", {}))
    
    with tabs[4]:
        render_profitability(plan.get("profit_projection", {}))
    
    with tabs[5]:
        render_risk_assessment(plan.get("risk_assessment", {}))
    
    with tabs[6]:
        render_energy_plan(plan.get("energy_plan", {}))
    
    with tabs[7]:
        st.subheader("📥 Export Plan")
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                "📄 Download Full Plan (JSON)",
                data=json.dumps(plan, indent=2, default=str),
                file_name=f"strategic_plan_{lat:.2f}_{lon:.2f}_{area_ha}ha.json",
                mime="application/json",
                use_container_width=True,
            )
        
        with col2:
            # Summary text
            summary_text = f"""
AgriMesh Strategic Farm Plan
============================
Location: ({lat:.4f}, {lon:.4f})
Area: {area_ha} ha
AEZ Zone: {summary.get('aez_zone', 'N/A')}
Land Class: {summary.get('land_suitability', 'N/A')}

Recommended Tier: {summary.get('recommended_tier', 'N/A')}
Capital Required: ${summary.get('capital_required_usd', 0):,.0f}
Annual Profit: ${summary.get('expected_annual_profit_usd', 0):,.0f}
Profit Probability: {summary.get('profit_probability_pct', 0):.0f}%
Risk Level: {summary.get('risk_level', 'N/A')}

Top Enterprises: {', '.join(summary.get('top_enterprises', []))}
Constraints: {', '.join(summary.get('key_constraints', []))}
"""
            st.download_button(
                "📝 Download Summary (TXT)",
                data=summary_text,
                file_name=f"plan_summary_{lat:.2f}_{lon:.2f}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        
        # Show raw JSON in expander
        with st.expander("View Raw JSON"):
            st.json(plan)

else:
    # Show instructions
    st.info("👈 Configure your farm parameters in the sidebar and click **Generate Strategic Plan** to begin.")
    
    # Show AEZ zones info
    st.subheader("📚 Zimbabwe Agro-Ecological Zones")
    
    for zone_id, zone_data in ZIMBABWE_AEZ_ZONES.items():
        with st.expander(f"Zone {zone_id}: {zone_data['description']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                rain = zone_data.get("rainfall_range", (0, 0))
                st.write(f"**Rainfall:** {rain[0]}-{rain[1]} mm")
                days = zone_data.get("growing_days", (0, 0))
                st.write(f"**Growing Days:** {days[0]}-{days[1]}")
                st.write(f"**Frost Risk:** {zone_data.get('frost_risk', 'N/A')}")
            
            with col2:
                st.write("**Suitable Crops:**")
                for crop in zone_data.get("suitable_crops", [])[:5]:
                    st.write(f"  • {crop.replace('_', ' ').title()}")
                
                st.write("**Suitable Livestock:**")
                for ls in zone_data.get("suitable_livestock", [])[:3]:
                    st.write(f"  • {ls.replace('_', ' ').title()}")
