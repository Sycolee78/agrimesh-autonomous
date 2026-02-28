"""
Optimization Analysis - Pareto Frontier Visualization

Explore the trade-off between water savings and yield,
with interactive parameter tuning.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

import pandas as pd
import streamlit as st
import altair as alt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.sim.pareto_tuning import run_pareto_tuning, recommend_config
from src.sim.yield_model import CropWaterProfile, CROP_PROFILES, calculate_yield_factor

st.set_page_config(
    page_title="Optimization - AgriMesh",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Multi-Objective Optimization")
st.caption("Explore the Pareto frontier: water savings vs yield performance")

# Sidebar controls
st.sidebar.header("⚙️ Tuning Configuration")

simulation_days = st.sidebar.slider(
    "Simulation Days",
    min_value=30,
    max_value=120,
    value=60,
    step=15
)

max_trials = st.sidebar.slider(
    "Max Trials",
    min_value=50,
    max_value=500,
    value=100,
    step=50,
    help="More trials = better coverage but slower"
)

st.sidebar.divider()
st.sidebar.header("🎯 Recommendation Mode")

preference = st.sidebar.radio(
    "Optimization Goal",
    options=["balanced", "water_saver", "yield_maximizer"],
    index=0,
    help="""
    - **balanced**: Equal priority to water and yield
    - **water_saver**: Prioritize water conservation
    - **yield_maximizer**: Prioritize maximum yield
    """
)

# Run optimization
if st.sidebar.button("🚀 Run Pareto Analysis", type="primary", use_container_width=True):
    with st.spinner(f"Running {max_trials} parameter combinations..."):
        try:
            results = run_pareto_tuning(
                days=simulation_days,
                max_trials=max_trials
            )
            recommendation = recommend_config(results, preference=preference)
            
            st.session_state["tuning_results"] = results
            st.session_state["recommendation"] = recommendation
            
            st.success(f"✅ Found {results['metadata']['pareto_optimal_count']} Pareto-optimal configurations")
        except Exception as e:
            st.error(f"Optimization failed: {e}")
            import traceback
            st.code(traceback.format_exc())

# Display results
if "tuning_results" in st.session_state:
    results = st.session_state["tuning_results"]
    recommendation = st.session_state.get("recommendation", {})
    
    st.header("🌾 Optimization Results")
    
    # Summary metrics
    metadata = results.get("metadata", {})
    pareto_points = results.get("pareto_frontier", [])
    all_points = results.get("all_points", [])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trials", metadata.get("total_trials", len(all_points)))
    with col2:
        st.metric("Pareto-Optimal", metadata.get("pareto_optimal_count", len(pareto_points)))
    with col3:
        if pareto_points:
            min_water = min(p["water_used"] for p in pareto_points)
            st.metric("Min Water", f"{min_water:,.0f} L")
    with col4:
        if pareto_points:
            max_yield = max(p["yield_tons_per_ha"] for p in pareto_points)
            st.metric("Max Yield", f"{max_yield:.2f} t/ha")
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Pareto Frontier", 
        "📊 All Results", 
        "⚙️ Recommended Config",
        "🔬 Yield Model"
    ])
    
    with tab1:
        st.subheader("Pareto Frontier: Water vs Yield Trade-off")
        
        if all_points:
            # Prepare data
            all_df = pd.DataFrame([
                {
                    "water_used": p["water_used"],
                    "yield": p["yield_tons_per_ha"],
                    "stress": p.get("stress_events", 0),
                    "pareto": p.get("is_pareto_optimal", False),
                    "config": str(p["config"])
                }
                for p in all_points
            ])
            
            pareto_df = pd.DataFrame([
                {
                    "water_used": p["water_used"],
                    "yield": p["yield_tons_per_ha"],
                    "stress": p.get("stress_events", 0),
                }
                for p in pareto_points
            ])
            
            # All points (gray)
            base = alt.Chart(all_df).mark_circle(size=60, opacity=0.3, color="#bdc3c7").encode(
                x=alt.X("water_used:Q", title="Water Used (liters)"),
                y=alt.Y("yield:Q", title="Yield (t/ha)"),
                tooltip=["water_used:Q", "yield:Q", "stress:Q"]
            )
            
            # Pareto line
            pareto_line = alt.Chart(pareto_df).mark_line(
                color="#e74c3c",
                strokeWidth=2
            ).encode(
                x="water_used:Q",
                y="yield:Q",
                order="water_used:Q"
            )
            
            # Pareto points
            pareto_circles = alt.Chart(pareto_df).mark_circle(
                size=120,
                color="#e74c3c"
            ).encode(
                x="water_used:Q",
                y="yield:Q",
                tooltip=["water_used:Q", "yield:Q", "stress:Q"]
            )
            
            # Recommended point
            if recommendation:
                rec_df = pd.DataFrame([{
                    "water_used": recommendation.get("water_used", 0),
                    "yield": recommendation.get("yield_tons_per_ha", 0)
                }])
                rec_point = alt.Chart(rec_df).mark_star(
                    size=400,
                    color="#2ecc71"
                ).encode(
                    x="water_used:Q",
                    y="yield:Q"
                )
                chart = (base + pareto_line + pareto_circles + rec_point)
            else:
                chart = (base + pareto_line + pareto_circles)
            
            chart = chart.properties(
                height=500,
                title="Pareto Frontier: Each point is a parameter configuration"
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            st.markdown("""
            **Legend:**
            - 🔴 Red line/points = Pareto-optimal configurations (no config is better in both dimensions)
            - ⭐ Green star = Recommended configuration for your selected preference
            - Gray points = All tested configurations
            """)
            
            # Pareto table
            st.subheader("Pareto-Optimal Configurations")
            pareto_table = pd.DataFrame([
                {
                    "Water Used (L)": f"{p['water_used']:,.0f}",
                    "Yield (t/ha)": f"{p['yield_tons_per_ha']:.3f}",
                    "Stress Events": p.get("stress_events", 0),
                    "Target Moisture": p["config"].get("target_moisture", "N/A"),
                }
                for p in sorted(pareto_points, key=lambda x: x["water_used"])
            ])
            st.dataframe(pareto_table, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("All Optimization Results")
        
        if all_points:
            # Results table
            results_df = pd.DataFrame([
                {
                    "Water Used (L)": f"{p['water_used']:,.0f}",
                    "Yield (t/ha)": f"{p['yield_tons_per_ha']:.3f}",
                    "Stress Events": p.get("stress_events", 0),
                    "Pareto": "✅" if p.get("is_pareto_optimal") else "",
                    "Config": str(p["config"])
                }
                for p in sorted(all_points, key=lambda x: -x["yield_tons_per_ha"])
            ])
            st.dataframe(results_df, use_container_width=True, hide_index=True, height=500)
            
            # Download
            csv = results_df.to_csv(index=False)
            st.download_button(
                "📥 Download Results CSV",
                csv,
                "pareto_results.csv",
                "text/csv"
            )
    
    with tab3:
        st.subheader(f"⚙️ Recommended Configuration ({preference})")
        
        if recommendation:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Performance")
                st.metric("Water Used", f"{recommendation.get('water_used', 0):,.0f} L")
                st.metric("Expected Yield", f"{recommendation.get('yield_tons_per_ha', 0):.2f} t/ha")
                st.metric("Stress Events", recommendation.get("stress_events", 0))
            
            with col2:
                st.markdown("### Parameters")
                st.code(json.dumps(recommendation.get("config", {}), indent=2), language="json")
            
            st.divider()
            
            st.markdown("### 📋 Apply This Configuration")
            st.markdown("""
            To use this optimized configuration in your farm simulation:
            
            1. **In Simulation UI:** Update irrigation thresholds in sidebar
            2. **In Code:** Pass these parameters to the IrrigationAgent
            3. **Export:** Download configuration below
            """)
            
            config_json = json.dumps({
                "preference": preference,
                "config": recommendation.get("config", {}),
                "expected_water_liters": recommendation.get("water_used", 0),
                "expected_yield_t_ha": recommendation.get("yield_tons_per_ha", 0)
            }, indent=2)
            
            st.download_button(
                "📥 Download Config JSON",
                config_json,
                f"irrigation_config_{preference}.json",
                "application/json"
            )
        else:
            st.info("No recommendation available. Run the optimization first.")
    
    with tab4:
        st.subheader("🔬 Non-Linear Yield Model")
        
        st.markdown("""
        ### Crop Yield Response Curves
        
        The AgriMesh yield model captures the non-linear relationship between 
        soil moisture and crop yield, including:
        
        - **Optimal moisture range** — where yield is maximized
        - **Wilting point** — below which yield drops sharply
        - **Waterlogging penalty** — too much water reduces yield
        - **Growth stage sensitivity** — flowering is critical
        """)
        
        # Select crop
        crop = st.selectbox("Select Crop", options=list(CROP_PROFILES.keys()), index=0)
        profile = CROP_PROFILES.get(crop, CROP_PROFILES["maize"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Crop Parameters")
            st.json({
                "optimal_moisture_min": profile.optimal_moisture_min,
                "optimal_moisture_max": profile.optimal_moisture_max,
                "wilting_point": profile.wilting_point,
                "saturation_point": profile.saturation_point,
                "max_yield_potential": profile.max_yield_potential,
                "drought_sensitivity": profile.drought_sensitivity,
                "waterlog_sensitivity": profile.waterlog_sensitivity
            })
        
        with col2:
            st.markdown("#### Growth Stage Demand")
            stage_demand = {str(k.value): v for k, v in profile.stage_demand.items()}
            st.json(stage_demand)
        
        # Generate yield curve
        st.markdown("#### Moisture → Yield Response")
        
        moisture_range = [i/100 for i in range(10, 95, 2)]
        
        yield_data = []
        for stage in ["vegetative", "flowering", "grain_fill", "maturity"]:
            # Map stage days for calculate_yield_factor
            stage_days = {"vegetative": 25, "flowering": 50, "grain_fill": 75, "maturity": 100}
            day = stage_days.get(stage, 50)
            for m in moisture_range:
                y = calculate_yield_factor(m, crop, day)
                yield_data.append({
                    "moisture": m,
                    "yield_factor": y,
                    "stage": stage
                })
        
        yield_df = pd.DataFrame(yield_data)
        
        yield_curve = alt.Chart(yield_df).mark_line(strokeWidth=2).encode(
            x=alt.X("moisture:Q", title="Soil Moisture (0-1)", scale=alt.Scale(domain=[0.1, 0.95])),
            y=alt.Y("yield_factor:Q", title="Yield Factor (1.0 = optimal)"),
            color=alt.Color("stage:N", title="Growth Stage"),
            tooltip=["moisture:Q", "yield_factor:Q", "stage:N"]
        ).properties(
            height=400,
            title=f"{crop.title()} Yield Response by Growth Stage"
        )
        
        # Add optimal zone
        optimal_zone = alt.Chart(pd.DataFrame({
            "x": [profile.optimal_moisture_min],
            "x2": [profile.optimal_moisture_max]
        })).mark_rect(opacity=0.2, color="#2ecc71").encode(
            x="x:Q",
            x2="x2:Q"
        )
        
        st.altair_chart(optimal_zone + yield_curve, use_container_width=True)
        
        st.caption(f"Green shaded area = optimal moisture range ({profile.optimal_moisture_min:.0%} - {profile.optimal_moisture_max:.0%})")

# Instructions
if "tuning_results" not in st.session_state:
    st.info("""
    👆 Configure tuning parameters in the sidebar and click **Run Pareto Analysis** to explore 
    the trade-off between water usage and yield.
    
    ### What is Pareto Optimization?
    
    The **Pareto frontier** shows configurations where you cannot improve one objective 
    (water savings) without sacrificing the other (yield). All points on the frontier 
    are "optimal" in different ways.
    
    ### Key Insight
    
    Our non-linear yield model shows that **smart irrigation can save significant water 
    while maintaining yield** — because crops have an optimal moisture range, 
    not a "more is better" relationship with water.
    """)
    
    # Show pre-computed results summary
    st.divider()
    st.header("📊 Previous Optimization Results")
    
    # Check for saved results
    results_path = Path(__file__).parent.parent.parent / "logs" / "tuning" / "pareto_frontier.json"
    if results_path.exists():
        with open(results_path) as f:
            saved_results = json.load(f)
        
        st.success(f"Loaded saved results from {saved_results['metadata'].get('generated_at', 'unknown date')}")
        
        pareto_points = saved_results.get("pareto_frontier", [])
        if pareto_points:
            summary_df = pd.DataFrame([
                {
                    "Water Used (L)": f"{p['water_used']:,.0f}",
                    "Yield (t/ha)": f"{p['yield_tons_per_ha']:.3f}",
                    "Config": str(p["config"])
                }
                for p in sorted(pareto_points, key=lambda x: x["water_used"])[:5]
            ])
            st.caption("Top 5 Pareto-optimal configurations (sorted by water usage)")
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("No saved results found. Run an optimization to see results.")
