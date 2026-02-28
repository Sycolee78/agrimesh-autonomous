"""
AI Advisor - LLM-Powered Farm Decision Explanation

Uses the LLM reasoning agent to:
- Explain irrigation decisions in plain language
- Generate daily/weekly summaries
- Answer farmer questions
- Provide actionable recommendations
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.reasoning.llm_explainer import (
    AgriMeshExplainer, 
    OllamaBackend, 
    OpenAIBackend, 
    AnthropicBackend,
    ExplanationRequest
)
from src.data.weather_client import ZIMBABWE_LOCATIONS

st.set_page_config(
    page_title="AI Advisor - AgriMesh",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Farm Advisor")
st.caption("Natural language explanations and recommendations powered by LLM")

# Sidebar configuration
st.sidebar.header("⚙️ LLM Configuration")

backend = st.sidebar.selectbox(
    "LLM Backend",
    options=["ollama", "openai", "anthropic"],
    index=0,
    help="""
    - **ollama**: Local models (free, private)
    - **openai**: GPT-4 (requires API key)
    - **anthropic**: Claude (requires API key)
    """
)

if backend == "ollama":
    model = st.sidebar.text_input("Model Name", value="llama3.2")
    api_key = None
    st.sidebar.caption("Make sure Ollama is running: `ollama serve`")
elif backend == "openai":
    model = st.sidebar.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    api_key = st.sidebar.text_input("API Key", type="password")
else:
    model = st.sidebar.selectbox("Model", ["claude-sonnet-4-20250514", "claude-3-haiku-20240307"])
    api_key = st.sidebar.text_input("API Key", type="password")

# Initialize explainer
@st.cache_resource
def get_explainer(backend_name: str, model: str, api_key: Optional[str] = None):
    """Create appropriate backend and explainer."""
    if backend_name == "ollama":
        backend = OllamaBackend(model=model)
    elif backend_name == "openai":
        backend = OpenAIBackend(model=model, api_key=api_key)
    elif backend_name == "anthropic":
        backend = AnthropicBackend(model=model, api_key=api_key)
    else:
        backend = OllamaBackend(model="llama3")
    
    return AgriMeshExplainer(backend=backend)

# Farm context for explanations
st.sidebar.divider()
st.sidebar.header("🌾 Farm Context")

location = st.sidebar.selectbox(
    "Location",
    options=list(ZIMBABWE_LOCATIONS.keys()),
    index=0
)

crop = st.sidebar.selectbox(
    "Primary Crop",
    options=["maize", "sorghum", "groundnuts", "vegetables", "potato"],
    index=0
)

growth_stage = st.sidebar.selectbox(
    "Growth Stage",
    options=["germination", "vegetative", "flowering", "grain_fill", "maturity"],
    index=1
)

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Ask the Advisor",
    "📊 Decision Explainer",
    "📝 Daily Summary",
    "🎓 Learning Mode"
])

with tab1:
    st.header("💬 Ask Your Farm Advisor")
    
    st.markdown("""
    Ask any question about your farm, crops, irrigation, or AgriMesh recommendations.
    The AI advisor uses your farm context to provide relevant answers.
    """)
    
    # Sample questions
    st.markdown("**Quick questions:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Why less water today?"):
            st.session_state["user_question"] = "Why did you recommend less irrigation today?"
    with col2:
        if st.button("When to harvest?"):
            st.session_state["user_question"] = f"When should I harvest my {crop} crop?"
    with col3:
        if st.button("Weather impact?"):
            st.session_state["user_question"] = "How will this week's weather affect my irrigation needs?"
    
    # User input
    user_question = st.text_area(
        "Your question:",
        value=st.session_state.get("user_question", ""),
        height=100,
        placeholder="e.g., Why did the system recommend irrigating today?"
    )
    
    if st.button("🚀 Ask Advisor", type="primary"):
        if not user_question:
            st.warning("Please enter a question")
        else:
            try:
                explainer = get_explainer(backend, model, api_key)
                
                # Build context
                context = {
                    "location": location,
                    "coordinates": ZIMBABWE_LOCATIONS[location],
                    "crop": crop,
                    "growth_stage": growth_stage,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "soil_moisture": 0.45,  # Example
                    "recent_rainfall_mm": 12.5,  # Example
                }
                
                with st.spinner("Thinking..."):
                    response = explainer.answer_question(
                        question=user_question,
                        farm_state=context,
                        recent_decisions=[]
                    )
                
                st.markdown("### 🤖 Advisor Response")
                st.markdown(response)
                
                # Clear the question
                st.session_state["user_question"] = ""
                
            except Exception as e:
                st.error(f"Error: {e}")
                if "connection" in str(e).lower():
                    st.info("Make sure Ollama is running: `ollama serve`")

with tab2:
    st.header("📊 Decision Explainer")
    
    st.markdown("""
    Enter an irrigation decision and get a natural language explanation 
    of why the agent made that choice.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Conditions")
        soil_moisture = st.slider("Soil Moisture", 0.0, 1.0, 0.42, 0.01)
        temperature = st.slider("Temperature (°C)", 15.0, 45.0, 32.0, 0.5)
        recent_rain = st.slider("Rain Last 24h (mm)", 0.0, 50.0, 5.0, 0.5)
        forecast_rain = st.slider("Forecast Rain Next 24h (mm)", 0.0, 50.0, 15.0, 0.5)
    
    with col2:
        st.subheader("Agent Decision")
        action = st.selectbox(
            "Decision",
            options=["irrigate", "skip_irrigation", "reduce_irrigation", "delay_irrigation"]
        )
        irrigation_amount = st.slider("Amount (liters)", 0, 500, 150, 10) if action == "irrigate" else 0
        confidence = st.slider("Confidence", 0.0, 1.0, 0.85, 0.01)
    
    if st.button("🔍 Explain Decision", type="primary"):
        try:
            explainer = get_explainer(backend, model, api_key)
            
            decision = {
                "action": action,
                "irrigation_liters": irrigation_amount,
                "confidence": confidence,
                "conditions": {
                    "soil_moisture": soil_moisture,
                    "temperature_c": temperature,
                    "recent_rainfall_mm": recent_rain,
                    "forecast_rainfall_mm": forecast_rain,
                    "crop": crop,
                    "growth_stage": growth_stage,
                    "location": location
                }
            }
            
            with st.spinner("Generating explanation..."):
                request = ExplanationRequest(
                    cycle_id="manual-query",
                    decision_log={
                        "action": action,
                        "rationale": f"Conditions: moisture={soil_moisture}, temp={temperature}°C, rain={recent_rain}mm",
                        "action_plan": {"irrigation_by_plot_liters": {"main": irrigation_amount}}
                    },
                    outcome_log={
                        "actual_changes": {
                            "soil_moisture_before": {"main": soil_moisture},
                            "soil_moisture_after": {"main": soil_moisture + 0.05 if action == "irrigate" else soil_moisture},
                        },
                        "kpi_delta": {
                            "water_use_efficiency": 0.75,
                            "yield_estimate_tons_per_ha": 4.5,
                        }
                    },
                    farm_state_summary={
                        "temperature_c": temperature,
                        "rainfall_mm": recent_rain,
                        "crop": crop,
                        "growth_stage": growth_stage,
                        "location": location
                    }
                )
                explanation = explainer.explain_decision(request)
            
            st.markdown("### 💡 Explanation")
            st.markdown(f"**Summary:** {explanation.summary}")
            st.markdown(explanation.detailed)
            
            # Also show the raw decision data
            with st.expander("📋 Raw Decision Data"):
                st.json({
                    "action": action,
                    "irrigation_liters": irrigation_amount,
                    "confidence": confidence,
                    "conditions": {
                        "soil_moisture": soil_moisture,
                        "temperature_c": temperature,
                        "recent_rainfall_mm": recent_rain,
                        "forecast_rainfall_mm": forecast_rain,
                    }
                })
                
        except Exception as e:
            st.error(f"Error: {e}")

with tab3:
    st.header("📝 Daily Summary Generator")
    
    st.markdown("""
    Generate a natural language summary of farm operations for a specific day.
    Perfect for record-keeping or sharing with farm workers.
    """)
    
    summary_date = st.date_input(
        "Date",
        value=datetime.now() - timedelta(days=1)
    )
    
    # Example day data (in real implementation, this would come from logs)
    st.subheader("📊 Day's Data")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Weather**")
        day_temp_max = st.number_input("Max Temp (°C)", value=33.5)
        day_temp_min = st.number_input("Min Temp (°C)", value=18.2)
        day_rain = st.number_input("Rainfall (mm)", value=8.5)
    
    with col2:
        st.markdown("**Operations**")
        irrigation_events = st.number_input("Irrigation Events", value=2, min_value=0)
        total_water = st.number_input("Total Water (L)", value=320)
        alerts_count = st.number_input("Alerts Generated", value=1, min_value=0)
    
    if st.button("📝 Generate Summary", type="primary"):
        try:
            explainer = get_explainer(backend, model, api_key)
            
            day_data = {
                "date": summary_date.strftime("%Y-%m-%d"),
                "location": location,
                "crop": crop,
                "growth_stage": growth_stage,
                "weather": {
                    "temperature_max_c": day_temp_max,
                    "temperature_min_c": day_temp_min,
                    "rainfall_mm": day_rain
                },
                "operations": {
                    "irrigation_events": irrigation_events,
                    "total_water_liters": total_water,
                    "alerts": alerts_count
                }
            }
            
            with st.spinner("Generating summary..."):
                summary = explainer.generate_daily_summary(
                    date=summary_date.strftime("%Y-%m-%d"),
                    weather={
                        "temperature_max_c": day_temp_max,
                        "temperature_min_c": day_temp_min,
                        "rainfall_mm": day_rain
                    },
                    decisions=[{"action_plan": {"irrigation_by_plot_liters": {"main": total_water}}}],
                    kpis={
                        "avg_moisture": 0.55,
                        "yield_estimate_tons_per_ha": 4.5,
                        "growth_stage": growth_stage
                    },
                    events=[f"{irrigation_events} irrigation events", f"{alerts_count} alerts generated"]
                )
            
            st.markdown("### 📋 Daily Summary")
            st.markdown(f"**Weather:** {summary.weather_summary}")
            st.markdown(f"**Irrigation:** {summary.irrigation_summary}")
            st.markdown(f"**Yield Outlook:** {summary.yield_outlook}")
            st.markdown(f"**Tomorrow:** {summary.tomorrow_plan}")
            
            # Download option
            full_summary = f"""# Daily Farm Summary - {summary_date}

## Weather
{summary.weather_summary}

## Irrigation
{summary.irrigation_summary}

## Yield Outlook
{summary.yield_outlook}

## Tomorrow's Plan
{summary.tomorrow_plan}
"""
            st.download_button(
                "📥 Download Summary",
                full_summary,
                f"farm_summary_{summary_date}.md",
                "text/markdown"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")

with tab4:
    st.header("🎓 Learning Mode")
    
    st.markdown("""
    Interactive learning about AgriMesh concepts and best practices.
    Ask questions or explore topics.
    """)
    
    # Topic cards
    topics = [
        {
            "title": "🌱 Crop Water Requirements",
            "description": "Learn how different crops and growth stages affect water needs",
            "prompt": "Explain how water requirements change through maize growth stages, and why flowering is the critical period."
        },
        {
            "title": "🌍 Zimbabwe AEZ Zones",
            "description": "Understand agro-ecological zones and their implications",
            "prompt": "Explain Zimbabwe's 5 agro-ecological zones and what crops grow best in each. Include rainfall expectations."
        },
        {
            "title": "💧 Smart Irrigation",
            "description": "How AgriMesh optimizes water usage",
            "prompt": "Explain how smart irrigation systems achieve water savings without reducing yield. What's the key insight about optimal moisture ranges?"
        },
        {
            "title": "📊 Yield Optimization",
            "description": "Maximizing crop yields sustainably",
            "prompt": "What are the top 5 factors that influence maize yield in Zimbabwe, and how can a farmer optimize each?"
        }
    ]
    
    col1, col2 = st.columns(2)
    
    for i, topic in enumerate(topics):
        col = col1 if i % 2 == 0 else col2
        with col:
            with st.container(border=True):
                st.markdown(f"### {topic['title']}")
                st.caption(topic['description'])
                if st.button("Learn More", key=f"learn_{i}"):
                    st.session_state["learning_topic"] = topic
    
    if "learning_topic" in st.session_state:
        topic = st.session_state["learning_topic"]
        
        st.divider()
        st.subheader(f"📚 {topic['title']}")
        
        try:
            explainer = get_explainer(backend, model, api_key)
            
            with st.spinner("Loading lesson..."):
                response = explainer.answer_question(
                    question=topic["prompt"],
                    farm_state={"location": location, "crop": crop, "mode": "educational"},
                    recent_decisions=[]
                )
            
            st.markdown(response)
            
            # Follow-up question
            follow_up = st.text_input("Have a follow-up question?")
            if follow_up and st.button("Ask"):
                with st.spinner("Thinking..."):
                    follow_response = explainer.answer_question(
                        question=follow_up,
                        farm_state={"previous_topic": topic["title"], "location": location},
                        recent_decisions=[]
                    )
                st.markdown(follow_response)
                
        except Exception as e:
            st.error(f"Error: {e}")
            if "connection" in str(e).lower():
                st.info("Make sure Ollama is running: `ollama serve`")

# Footer
st.divider()
st.caption("""
**Note:** The AI Advisor uses large language models to generate explanations.
While trained on agricultural best practices, always verify critical decisions
with local agronomists or extension officers.
""")
