"""
Weather Analysis - Real Zimbabwe Weather Data

Visualizes historical and forecast weather data from Open-Meteo API
for key Zimbabwe agricultural locations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st
import altair as alt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.weather_client import OpenMeteoClient, ZIMBABWE_LOCATIONS

st.set_page_config(
    page_title="Weather Analysis - AgriMesh",
    page_icon="🌦️",
    layout="wide"
)

st.title("🌦️ Zimbabwe Weather Analysis")
st.caption("Real historical and forecast data from Open-Meteo API")

# Initialize weather client
@st.cache_resource
def get_weather_client():
    return OpenMeteoClient()

client = get_weather_client()

# Sidebar controls
st.sidebar.header("📍 Location")
location_name = st.sidebar.selectbox(
    "Select Location",
    options=list(ZIMBABWE_LOCATIONS.keys()),
    index=0,
    help="Major agricultural locations in Zimbabwe"
)

coords = ZIMBABWE_LOCATIONS[location_name]
st.sidebar.caption(f"Coordinates: ({coords['lat']:.2f}, {coords['lon']:.2f})")

st.sidebar.divider()
st.sidebar.header("📅 Date Range")

# Date range selection
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime(2024, 11, 1),
        min_value=datetime(2000, 1, 1),
        max_value=datetime.now()
    )
with col2:
    end_date = st.date_input(
        "End Date",
        value=datetime(2025, 3, 31),
        min_value=datetime(2000, 1, 1),
        max_value=datetime.now() + timedelta(days=16)
    )

# Fetch data button
if st.sidebar.button("🔄 Fetch Weather Data", type="primary", use_container_width=True):
    with st.spinner(f"Fetching weather data for {location_name}..."):
        try:
            from datetime import date as date_type
            data = client.get_historical(
                location=location_name.lower().replace(" ", "_"),
                start_date=date_type(start_date.year, start_date.month, start_date.day),
                end_date=date_type(end_date.year, end_date.month, end_date.day)
            )
            # Convert DailyWeather objects to dicts for display
            data_dicts = [
                {
                    "date": d.date.isoformat(),
                    "temperature_max_c": d.temperature_max_c,
                    "temperature_min_c": d.temperature_min_c,
                    "precipitation_mm": d.precipitation_mm,
                    "relative_humidity_pct": d.humidity_mean_pct,
                }
                for d in data
            ]
            st.session_state["weather_data"] = data_dicts
            st.session_state["weather_location"] = location_name
            st.success(f"✅ Loaded {len(data)} days of weather data")
        except Exception as e:
            st.error(f"Failed to fetch weather data: {e}")
            import traceback
            st.code(traceback.format_exc())

# Also fetch forecast
if st.sidebar.button("📡 Get 16-Day Forecast", use_container_width=True):
    with st.spinner(f"Fetching forecast for {location_name}..."):
        try:
            forecast = client.get_forecast(location=location_name.lower().replace(" ", "_"))
            # Convert to dicts for display
            forecast_dicts = [
                {
                    "date": d.date.isoformat(),
                    "temperature_max_c": d.temperature_max_c,
                    "temperature_min_c": d.temperature_min_c,
                    "precipitation_mm": d.precipitation_mm,
                }
                for d in forecast.daily
            ]
            st.session_state["forecast_data"] = forecast_dicts
            st.session_state["forecast_location"] = location_name
            st.success(f"✅ Loaded {len(forecast_dicts)} day forecast")
        except Exception as e:
            st.error(f"Failed to fetch forecast: {e}")
            import traceback
            st.code(traceback.format_exc())

# Display data
if "weather_data" in st.session_state and st.session_state["weather_data"]:
    data = st.session_state["weather_data"]
    location = st.session_state.get("weather_location", "Unknown")
    
    st.header(f"📊 Historical Weather: {location}")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_rain = df["precipitation_mm"].sum()
        st.metric("Total Rainfall", f"{total_rain:.0f} mm")
    with col2:
        avg_temp = df["temperature_max_c"].mean()
        st.metric("Avg Max Temp", f"{avg_temp:.1f}°C")
    with col3:
        rainy_days = (df["precipitation_mm"] > 1).sum()
        st.metric("Rainy Days (>1mm)", f"{rainy_days}")
    with col4:
        avg_humidity = df["relative_humidity_pct"].mean() if "relative_humidity_pct" in df.columns else 0
        st.metric("Avg Humidity", f"{avg_humidity:.0f}%")
    
    st.divider()
    
    # Charts
    tab1, tab2, tab3, tab4 = st.tabs(["🌧️ Rainfall", "🌡️ Temperature", "💧 Combined", "📋 Data Table"])
    
    with tab1:
        # Rainfall chart
        rain_chart = alt.Chart(df).mark_bar(color="#3498db").encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("precipitation_mm:Q", title="Rainfall (mm)"),
            tooltip=["date:T", "precipitation_mm:Q"]
        ).properties(
            height=400,
            title="Daily Rainfall"
        )
        st.altair_chart(rain_chart, use_container_width=True)
        
        # Monthly summary
        df["month"] = df["date"].dt.to_period("M").astype(str)
        monthly = df.groupby("month")["precipitation_mm"].sum().reset_index()
        monthly_chart = alt.Chart(monthly).mark_bar(color="#2ecc71").encode(
            x=alt.X("month:N", title="Month"),
            y=alt.Y("precipitation_mm:Q", title="Total Rainfall (mm)"),
            tooltip=["month:N", "precipitation_mm:Q"]
        ).properties(
            height=300,
            title="Monthly Rainfall Totals"
        )
        st.altair_chart(monthly_chart, use_container_width=True)
    
    with tab2:
        # Temperature chart
        temp_df = df.melt(
            id_vars=["date"],
            value_vars=["temperature_max_c", "temperature_min_c"],
            var_name="type",
            value_name="temperature"
        )
        temp_df["type"] = temp_df["type"].map({
            "temperature_max_c": "Max",
            "temperature_min_c": "Min"
        })
        
        temp_chart = alt.Chart(temp_df).mark_line().encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("temperature:Q", title="Temperature (°C)"),
            color=alt.Color("type:N", scale=alt.Scale(
                domain=["Max", "Min"],
                range=["#e74c3c", "#3498db"]
            )),
            tooltip=["date:T", "type:N", "temperature:Q"]
        ).properties(
            height=400,
            title="Daily Temperature Range"
        )
        st.altair_chart(temp_chart, use_container_width=True)
    
    with tab3:
        # Combined: rainfall bars + temperature line
        base = alt.Chart(df).encode(x=alt.X("date:T", title="Date"))
        
        bars = base.mark_bar(color="#3498db", opacity=0.6).encode(
            y=alt.Y("precipitation_mm:Q", title="Rainfall (mm)")
        )
        
        line = base.mark_line(color="#e74c3c", strokeWidth=2).encode(
            y=alt.Y("temperature_max_c:Q", title="Max Temp (°C)", axis=alt.Axis(orient="right"))
        )
        
        combined = alt.layer(bars, line).resolve_scale(y="independent").properties(
            height=400,
            title="Rainfall & Temperature Combined"
        )
        st.altair_chart(combined, use_container_width=True)
    
    with tab4:
        st.dataframe(
            df[["date", "temperature_max_c", "temperature_min_c", "precipitation_mm"]].rename(columns={
                "date": "Date",
                "temperature_max_c": "Max Temp (°C)",
                "temperature_min_c": "Min Temp (°C)",
                "precipitation_mm": "Rainfall (mm)"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"weather_{location.lower().replace(' ', '_')}_{start_date}_{end_date}.csv",
            "text/csv"
        )

# Display forecast
if "forecast_data" in st.session_state and st.session_state["forecast_data"]:
    forecast = st.session_state["forecast_data"]
    location = st.session_state.get("forecast_location", "Unknown")
    
    st.divider()
    st.header(f"📡 16-Day Forecast: {location}")
    
    df_forecast = pd.DataFrame(forecast)
    df_forecast["date"] = pd.to_datetime(df_forecast["date"])
    
    # Forecast summary
    col1, col2, col3 = st.columns(3)
    with col1:
        total_rain = df_forecast["precipitation_mm"].sum()
        st.metric("Expected Rainfall", f"{total_rain:.0f} mm")
    with col2:
        avg_temp = df_forecast["temperature_max_c"].mean()
        st.metric("Avg Max Temp", f"{avg_temp:.1f}°C")
    with col3:
        rainy_days = (df_forecast["precipitation_mm"] > 1).sum()
        st.metric("Rainy Days Expected", f"{rainy_days}")
    
    # Forecast chart
    forecast_chart = alt.Chart(df_forecast).mark_bar(color="#9b59b6").encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("precipitation_mm:Q", title="Rainfall (mm)"),
        tooltip=["date:T", "precipitation_mm:Q", "temperature_max_c:Q"]
    ).properties(
        height=300,
        title="16-Day Rainfall Forecast"
    )
    st.altair_chart(forecast_chart, use_container_width=True)

# Growing season analysis
st.divider()
st.header("🌱 Growing Season Analysis")

st.markdown("""
### Zimbabwe Growing Seasons
- **Main Season (Wet):** November - March
- **Dry Season:** April - October
- **Critical Periods:** December-February (peak rainfall, maize flowering)

### AEZ Rainfall Expectations
| Zone | Annual Rainfall | Growing Days |
|------|-----------------|--------------|
| I | >1000mm | 180+ |
| II | 750-1000mm | 150-180 |
| III | 650-800mm | 120-150 |
| IV | 450-650mm | 90-120 |
| V | <500mm | <90 |
""")

# Quick location comparison
st.subheader("📍 Quick Location Comparison")
if st.button("Compare All Locations (2024/25 Season)"):
    from datetime import date as date_type
    comparison_data = []
    progress = st.progress(0)
    
    for i, (loc_name, loc_coords) in enumerate(ZIMBABWE_LOCATIONS.items()):
        try:
            data = client.get_historical(
                location=loc_name,
                start_date=date_type(2024, 11, 1),
                end_date=date_type(2025, 3, 31)
            )
            total_rain = sum(d.precipitation_mm for d in data)
            avg_temp = sum(d.temperature_max_c for d in data) / len(data)
            comparison_data.append({
                "Location": loc_name.title(),
                "AEZ Zone": loc_coords.get("aez", "N/A"),
                "Total Rainfall (mm)": round(total_rain, 0),
                "Avg Max Temp (°C)": round(avg_temp, 1),
                "Rainy Days": sum(1 for d in data if d.precipitation_mm > 1)
            })
        except Exception as e:
            comparison_data.append({
                "Location": loc_name.title(),
                "AEZ Zone": loc_coords.get("aez", "N/A"),
                "Total Rainfall (mm)": "Error",
                "Avg Max Temp (°C)": "Error",
                "Rainy Days": "Error"
            })
        progress.progress((i + 1) / len(ZIMBABWE_LOCATIONS))
    
    progress.empty()
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

# Instructions
if "weather_data" not in st.session_state:
    st.info("👆 Select a location and click **Fetch Weather Data** to view historical weather patterns.")
