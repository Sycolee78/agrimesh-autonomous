"""
ML Farm Planner - AI-Powered Sustainable Farm Planning

Select a location on the map and get ML-generated recommendations for:
- Optimal crop selection with yield predictions
- Enterprise mix with synergies
- Capital requirements and ROI projections
- Sustainability assessment
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ml.planner import MLFarmPlanner

st.set_page_config(
    page_title="ML Farm Planner - AgriMesh",
    page_icon="🤖",
    layout="wide"
)

# Initialize planner
@st.cache_resource
def get_planner():
    return MLFarmPlanner(use_weather=True)

planner = get_planner()

# Zone colors for visualization
ZONE_COLORS = {
    "I": "#1a9850",
    "IIa": "#66bd63",
    "IIb": "#a6d96a",
    "III": "#d9ef8b",
    "IV": "#fee08b",
    "V": "#d73027",
}

# Quick-select cities
CITIES = [
    {"name": "Harare", "lat": -17.8292, "lon": 31.0522, "desc": "Zone IIb - Reliable rainfall"},
    {"name": "Bulawayo", "lat": -20.1539, "lon": 28.5802, "desc": "Zone IV - Semi-extensive"},
    {"name": "Mutare", "lat": -18.9707, "lon": 32.6709, "desc": "Zone I - High rainfall"},
    {"name": "Masvingo", "lat": -20.0744, "lon": 30.8328, "desc": "Zone III - Semi-intensive"},
    {"name": "Gweru", "lat": -19.4500, "lon": 29.8167, "desc": "Zone III - Semi-intensive"},
    {"name": "Chinhoyi", "lat": -17.3667, "lon": 30.2000, "desc": "Zone IIa - High rainfall"},
    {"name": "Chiredzi", "lat": -21.0500, "lon": 31.6667, "desc": "Zone V - Low rainfall"},
    {"name": "Nyanga", "lat": -18.2167, "lon": 32.7500, "desc": "Zone I - Eastern Highlands"},
]


def format_currency(value: float) -> str:
    if value >= 1000000:
        return f"${value/1000000:.1f}M"
    elif value >= 1000:
        return f"${value/1000:.1f}K"
    return f"${value:.0f}"


def render_yield_predictions(predictions: list):
    """Render yield predictions section."""
    st.subheader("🌾 Crop Yield Predictions")
    
    if not predictions:
        st.info("No yield predictions available.")
        return
    
    # Top yields chart
    df = pd.DataFrame([
        {
            "Crop": p["crop_name"],
            "Yield (t/ha)": p["predicted_yield_tons_ha"],
            "Confidence": f"{p['confidence']*100:.0f}%",
            "Range": f"{p['yield_range'][0]:.1f} - {p['yield_range'][1]:.1f}",
        }
        for p in predictions[:8]
    ])
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.bar_chart(df.set_index("Crop")["Yield (t/ha)"])
    
    with col2:
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Limiting factors
    with st.expander("View Limiting Factors"):
        for p in predictions[:5]:
            if p.get("limiting_factors"):
                factors = ", ".join(f.replace("_", " ") for f in p["limiting_factors"])
                st.write(f"**{p['crop_name']}:** {factors}")
            else:
                st.write(f"**{p['crop_name']}:** No major limitations")


def render_enterprise_recommendations(enterprises: list, area_ha: float):
    """Render enterprise recommendations."""
    st.subheader("🏆 Recommended Enterprise Mix")
    
    if not enterprises:
        st.info("No recommendations available.")
        return
    
    # Top 3 cards
    cols = st.columns(3)
    for i, ent in enumerate(enterprises[:3]):
        with cols[i]:
            medal = ["🥇", "🥈", "🥉"][i]
            risk_color = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(ent["risk_level"], "⚪")
            
            st.markdown(f"""
            <div style="background:#f0f2f6; padding:15px; border-radius:10px; text-align:center;">
                <h3 style="margin:0;">{medal} {ent['name']}</h3>
                <p style="margin:5px 0; font-size:24px; color:#1f77b4;">{ent['suitability_score']:.0f}</p>
                <p style="margin:0; font-size:12px;">Suitability Score</p>
                <hr style="margin:10px 0;">
                <p style="margin:5px 0;">📊 {ent['allocation_pct']:.0f}% of farm</p>
                <p style="margin:5px 0;">💰 ${ent['profit_potential_usd_ha']:,.0f}/ha profit</p>
                <p style="margin:5px 0;">{risk_color} {ent['risk_level'].title()} risk</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Full allocation table
    st.markdown("---")
    st.markdown("**Full Allocation Plan:**")
    
    alloc_data = []
    for ent in enterprises:
        allocated_ha = area_ha * ent["allocation_pct"] / 100
        capital = ent["capital_required_usd_ha"] * allocated_ha
        profit = ent["profit_potential_usd_ha"] * allocated_ha
        
        alloc_data.append({
            "Enterprise": ent["name"],
            "Type": ent["type"].replace("_", " ").title(),
            "Allocation": f"{ent['allocation_pct']:.0f}%",
            "Area (ha)": f"{allocated_ha:.1f}",
            "Capital": format_currency(capital),
            "Exp. Profit": format_currency(profit),
            "Score": f"{ent['suitability_score']:.0f}",
        })
    
    df = pd.DataFrame(alloc_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Reasons and constraints
    with st.expander("View Recommendations Logic"):
        for ent in enterprises[:5]:
            st.markdown(f"**{ent['name']}**")
            if ent.get("reasons"):
                for reason in ent["reasons"]:
                    st.write(f"  ✅ {reason}")
            if ent.get("constraints"):
                for constraint in ent["constraints"]:
                    st.write(f"  ⚠️ {constraint.replace('_', ' ').title()}")


def render_location_features(features: dict, aez_zone: str):
    """Render location analysis."""
    st.subheader("📍 Location Analysis")
    
    zone_color = ZONE_COLORS.get(aez_zone, "#gray")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("AEZ Zone", aez_zone)
        st.markdown(f"""
        <div style="background:{zone_color}; padding:5px 10px; border-radius:5px; color:white; text-align:center;">
            Zone {aez_zone}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        rainfall = features.get("annual_rainfall_norm", 0) * 1150 + 250
        st.metric("Est. Rainfall", f"{rainfall:.0f} mm")
    
    with col3:
        reliability = features.get("rainfall_reliability", 0) * 100
        st.metric("Reliability", f"{reliability:.0f}%")
    
    with col4:
        growing_days = features.get("growing_days_norm", 0) * 130 + 80
        st.metric("Growing Days", f"{growing_days:.0f}")
    
    # More features in expander
    with st.expander("All Location Features"):
        feature_table = [
            ("Soil Fertility", f"{features.get('soil_fertility_score', 0)*100:.0f}%"),
            ("Soil Depth", f"{features.get('soil_depth_score', 0)*100:.0f}%"),
            ("Drainage", f"{features.get('drainage_score', 0)*100:.0f}%"),
            ("Water Availability", f"{features.get('water_availability_score', 0)*100:.0f}%"),
            ("Flood Risk", f"{features.get('flood_risk_score', 0)*100:.0f}%"),
            ("Market Distance", f"{features.get('market_distance_norm', 0)*200:.0f} km"),
            ("Road Quality", f"{features.get('road_quality_score', 0)*100:.0f}%"),
            ("Electricity Access", f"{features.get('electricity_access_score', 0)*100:.0f}%"),
        ]
        
        col1, col2 = st.columns(2)
        for i, (name, value) in enumerate(feature_table):
            with col1 if i % 2 == 0 else col2:
                st.write(f"**{name}:** {value}")


def render_economics_summary(plan):
    """Render economic summary."""
    st.subheader("💰 Economic Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Capital Required", format_currency(plan.total_capital_required))
    
    with col2:
        st.metric("Annual Revenue", format_currency(plan.expected_annual_revenue))
    
    with col3:
        st.metric("Annual Profit", format_currency(plan.expected_annual_profit))
    
    with col4:
        st.metric("Expected ROI", f"{plan.expected_roi_pct:.1f}%")


def render_sustainability(plan):
    """Render sustainability section."""
    st.subheader("🌱 Sustainability Assessment")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Sustainability score gauge
        score = plan.sustainability_score
        color = "#2ecc71" if score >= 70 else "#f39c12" if score >= 40 else "#e74c3c"
        
        st.markdown(f"""
        <div style="background:{color}; padding:30px; border-radius:50%; width:120px; height:120px; 
                    display:flex; align-items:center; justify-content:center; margin:auto;">
            <div style="text-align:center;">
                <span style="font-size:32px; color:white; font-weight:bold;">{score:.0f}</span>
                <br><span style="font-size:12px; color:white;">/100</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"<p style='text-align:center; margin-top:10px;'><b>Sustainability Score</b></p>", 
                   unsafe_allow_html=True)
    
    with col2:
        # Risk assessment
        risk_color = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(plan.risk_assessment, "⚪")
        st.write(f"**Overall Risk:** {risk_color} {plan.risk_assessment.title()}")
        
        # Circular economy opportunities
        if plan.circular_economy_opportunities:
            st.write("**♻️ Circular Economy Opportunities:**")
            for opp in plan.circular_economy_opportunities:
                st.write(f"  • {opp}")


# Main UI
st.title("🤖 ML Farm Planner")
st.markdown("""
**AI-powered sustainable farm planning for Zimbabwe.**  
Select a location and get ML-generated recommendations for crops, livestock, and enterprise mix.
""")

# Sidebar inputs
with st.sidebar:
    st.header("📍 Location")
    
    # Quick select
    city_names = ["Custom"] + [c["name"] for c in CITIES]
    selected_city = st.selectbox(
        "Quick Select",
        city_names,
        format_func=lambda x: x if x == "Custom" else f"{x} - {next((c['desc'] for c in CITIES if c['name']==x), '')}"
    )
    
    if selected_city != "Custom":
        city = next(c for c in CITIES if c["name"] == selected_city)
        default_lat = city["lat"]
        default_lon = city["lon"]
    else:
        default_lat = -17.83
        default_lon = 31.05
    
    lat = st.number_input("Latitude", value=default_lat, min_value=-22.5, max_value=-15.5, format="%.4f")
    lon = st.number_input("Longitude", value=default_lon, min_value=25.0, max_value=33.0, format="%.4f")
    
    st.divider()
    
    st.header("🌾 Farm Parameters")
    area_ha = st.slider("Farm Area (ha)", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
    
    has_capital = st.checkbox("Set Capital Budget")
    capital = None
    if has_capital:
        capital = st.number_input("Available Capital (USD)", value=25000, min_value=1000, step=1000)
    
    labor_days = st.number_input("Labor (days/year)", value=1000, min_value=100, max_value=5000)
    
    st.divider()
    
    # Generate button
    generate = st.button("🚀 Generate ML Plan", type="primary", use_container_width=True)

# Main content
if generate:
    with st.spinner("🔄 Generating ML-powered farm plan..."):
        try:
            plan = planner.generate_plan(
                lat=lat,
                lon=lon,
                area_ha=area_ha,
                available_capital=capital,
                available_labor_days=labor_days,
            )
            
            st.success("✅ Plan generated successfully!")
            st.session_state["ml_plan"] = plan
            
        except Exception as e:
            st.error(f"Error generating plan: {e}")
            st.exception(e)

# Display plan
if "ml_plan" in st.session_state:
    plan = st.session_state["ml_plan"]
    
    # Summary metrics
    st.markdown("---")
    render_economics_summary(plan)
    
    st.markdown("---")
    
    # Tabs for detailed sections
    tabs = st.tabs([
        "📍 Location",
        "🌾 Yields",
        "🏆 Enterprises",
        "🌱 Sustainability",
        "📥 Export",
    ])
    
    with tabs[0]:
        render_location_features(plan.location_features, plan.aez_zone)
    
    with tabs[1]:
        render_yield_predictions(plan.yield_predictions)
    
    with tabs[2]:
        render_enterprise_recommendations(plan.recommended_enterprises, plan.area_ha)
    
    with tabs[3]:
        render_sustainability(plan)
    
    with tabs[4]:
        st.subheader("📥 Export Plan")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                "📄 Download JSON",
                data=plan.to_json(),
                file_name=f"ml_plan_{lat:.2f}_{lon:.2f}_{area_ha}ha.json",
                mime="application/json",
                use_container_width=True,
            )
        
        with col2:
            st.download_button(
                "📝 Download Summary",
                data=plan.summary(),
                file_name=f"ml_plan_summary_{lat:.2f}_{lon:.2f}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        
        with st.expander("View Raw JSON"):
            st.json(plan.to_dict())

else:
    # Instructions
    st.info("👈 Select a location and click **Generate ML Plan** to begin.")
    
    # Quick comparison feature
    st.subheader("🔍 Quick Location Comparison")
    st.markdown("Compare farm potential across different locations in Zimbabwe:")
    
    compare_locations = st.multiselect(
        "Select locations to compare",
        [c["name"] for c in CITIES],
        default=["Harare", "Bulawayo", "Mutare"],
    )
    
    if st.button("Compare Locations") and compare_locations:
        with st.spinner("Analyzing locations..."):
            coords = [(c["lat"], c["lon"]) for c in CITIES if c["name"] in compare_locations]
            comparison = planner.compare_locations(coords, area_ha=10.0)
            
            st.success("Comparison complete!")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                best_profit = comparison["best_by_profit"]
                city = next((c for c in CITIES if abs(c["lat"]-best_profit["lat"]) < 0.1), {"name": "Unknown"})
                st.metric("🏆 Best by Profit", city["name"], format_currency(best_profit["profit"]))
            
            with col2:
                best_roi = comparison["best_by_roi"]
                city = next((c for c in CITIES if abs(c["lat"]-best_roi["lat"]) < 0.1), {"name": "Unknown"})
                st.metric("📈 Best by ROI", city["name"], f"{best_roi['roi_pct']:.1f}%")
            
            with col3:
                best_sus = comparison["best_by_sustainability"]
                city = next((c for c in CITIES if abs(c["lat"]-best_sus["lat"]) < 0.1), {"name": "Unknown"})
                st.metric("🌱 Most Sustainable", city["name"], f"{best_sus['score']:.0f}/100")
