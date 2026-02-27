"""
LLM-based reasoning and explanation agent for AgriMesh.

Provides natural language explanations of agent decisions,
anomaly detection, and farmer-friendly summaries.

Supports multiple backends:
- Ollama (local, recommended for privacy)
- OpenAI API
- Anthropic Claude API
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import urllib.request


@dataclass
class ExplanationRequest:
    """Request for decision explanation."""
    cycle_id: str
    decision_log: Dict[str, Any]
    outcome_log: Optional[Dict[str, Any]] = None
    farm_state_summary: Optional[Dict[str, Any]] = None
    question: Optional[str] = None  # Specific question from farmer


@dataclass
class Explanation:
    """Generated explanation."""
    cycle_id: str
    summary: str  # One-line summary
    detailed: str  # Full explanation
    confidence: float  # 0-1
    recommendations: List[str]
    warnings: List[str]
    generated_at: datetime


@dataclass
class DailySummary:
    """Daily farm operations summary."""
    date: str
    weather_summary: str
    irrigation_summary: str
    yield_outlook: str
    alerts: List[str]
    tomorrow_plan: str


class LLMBackend:
    """Base class for LLM backends."""
    
    def complete(self, prompt: str, system: str = None, max_tokens: int = 500) -> str:
        raise NotImplementedError


class OllamaBackend(LLMBackend):
    """Ollama local LLM backend."""
    
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def complete(self, prompt: str, system: str = None, max_tokens: int = 500) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            }
        }
        
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except Exception as e:
            return f"[LLM Error: {e}]"


class OpenAIBackend(LLMBackend):
    """OpenAI API backend."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    def complete(self, prompt: str, system: str = None, max_tokens: int = 500) -> str:
        if not self.api_key:
            return "[Error: OPENAI_API_KEY not set]"
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM Error: {e}]"


class AnthropicBackend(LLMBackend):
    """Anthropic Claude API backend."""
    
    def __init__(self, model: str = "claude-3-haiku-20240307", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    
    def complete(self, prompt: str, system: str = None, max_tokens: int = 500) -> str:
        if not self.api_key:
            return "[Error: ANTHROPIC_API_KEY not set]"
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["content"][0]["text"]
        except Exception as e:
            return f"[LLM Error: {e}]"


# Prompt templates

SYSTEM_PROMPT = """You are an agricultural AI assistant for AgriMesh, a farm management system in Zimbabwe.

Your role is to explain farm operation decisions in clear, simple language that a farmer can understand.
Focus on practical implications and actionable insights.

Context:
- You operate in Zimbabwe's agricultural zones (AEZ I-V)
- Primary crops: maize, sorghum, groundnuts, potatoes, vegetables
- Primary concern: water efficiency during variable rainfall seasons
- Farmers may have limited technical background

Guidelines:
- Use simple, direct language
- Relate decisions to visible crop/weather conditions
- Quantify water and yield impacts when possible
- Always include actionable next steps
- Flag any concerning conditions prominently"""


EXPLAIN_DECISION_PROMPT = """Explain this irrigation decision to a farmer:

**Cycle:** {cycle_id}
**Weather:** Temperature {temp}°C, Rainfall {rain}mm
**Soil moisture before:** {moisture_before}
**Water applied:** {water_applied} liters

**Agent rationale:** {rationale}

**Results:**
- Soil moisture after: {moisture_after}
- Water use efficiency: {wue}
- Yield estimate: {yield_est} tons/ha

Generate a brief explanation (2-3 sentences) that:
1. Explains WHY this much water was applied
2. Notes if conditions were normal or concerning
3. Mentions expected crop impact"""


DAILY_SUMMARY_PROMPT = """Generate a daily farm summary for the farmer.

**Date:** {date}
**Weather:** High {temp_max}°C, Low {temp_min}°C, Rain {rain}mm
**Total water used:** {water_used} liters
**Average soil moisture:** {avg_moisture}%
**Yield estimate:** {yield_est} tons/ha
**Growth stage:** {growth_stage}

**Notable events:**
{events}

Generate a conversational summary (5-7 sentences) covering:
1. Weather conditions and their impact
2. Irrigation activity summary
3. Crop health/yield outlook
4. Any alerts or concerns
5. What to expect/do tomorrow"""


ANSWER_QUESTION_PROMPT = """A farmer asks: "{question}"

**Current farm state:**
{farm_state}

**Recent decisions:**
{recent_decisions}

Answer the farmer's question directly and helpfully. If you don't have enough information, say so.
Keep the answer concise (2-4 sentences) and practical."""


class AgriMeshExplainer:
    """
    LLM-based explainer for AgriMesh decisions.
    
    Usage:
        explainer = AgriMeshExplainer(backend=OllamaBackend("llama3"))
        explanation = explainer.explain_decision(request)
    """
    
    def __init__(self, backend: LLMBackend = None):
        self.backend = backend or OllamaBackend()
    
    def explain_decision(self, request: ExplanationRequest) -> Explanation:
        """Generate explanation for a single decision."""
        
        decision = request.decision_log
        outcome = request.outcome_log or {}
        
        # Extract relevant values
        rationale = decision.get("rationale", "No rationale provided")
        action = decision.get("action_plan", {})
        water_applied = sum(action.get("irrigation_by_plot_liters", {}).values())
        
        actual = outcome.get("actual_changes", {})
        kpi = outcome.get("kpi_delta", {})
        
        prompt = EXPLAIN_DECISION_PROMPT.format(
            cycle_id=request.cycle_id,
            temp=request.farm_state_summary.get("temperature_c", 25) if request.farm_state_summary else 25,
            rain=request.farm_state_summary.get("rainfall_mm", 0) if request.farm_state_summary else 0,
            moisture_before=actual.get("soil_moisture_before", {}).get("plot-1", "N/A"),
            water_applied=round(water_applied, 1),
            rationale=rationale,
            moisture_after=actual.get("soil_moisture_after", {}).get("plot-1", "N/A"),
            wue=kpi.get("water_use_efficiency", "N/A"),
            yield_est=kpi.get("yield_estimate_tons_per_ha", "N/A"),
        )
        
        response = self.backend.complete(prompt, system=SYSTEM_PROMPT)
        
        # Parse response (simple version - just use full response)
        return Explanation(
            cycle_id=request.cycle_id,
            summary=response.split(".")[0] + "." if "." in response else response[:100],
            detailed=response,
            confidence=0.8,  # Placeholder
            recommendations=[],
            warnings=[],
            generated_at=datetime.now(),
        )
    
    def generate_daily_summary(
        self,
        date: str,
        weather: Dict[str, float],
        decisions: List[Dict[str, Any]],
        kpis: Dict[str, float],
        events: List[str] = None,
    ) -> DailySummary:
        """Generate daily operations summary."""
        
        total_water = sum(
            sum(d.get("action_plan", {}).get("irrigation_by_plot_liters", {}).values())
            for d in decisions
        )
        
        prompt = DAILY_SUMMARY_PROMPT.format(
            date=date,
            temp_max=weather.get("temperature_max_c", 30),
            temp_min=weather.get("temperature_min_c", 18),
            rain=weather.get("rainfall_mm", 0),
            water_used=round(total_water, 1),
            avg_moisture=round(kpis.get("avg_moisture", 0.5) * 100, 1),
            yield_est=kpis.get("yield_estimate_tons_per_ha", 4.5),
            growth_stage=kpis.get("growth_stage", "vegetative"),
            events="\n".join(f"- {e}" for e in (events or ["Normal operations"])),
        )
        
        response = self.backend.complete(prompt, system=SYSTEM_PROMPT, max_tokens=400)
        
        # Parse into structured summary
        lines = response.strip().split("\n")
        
        return DailySummary(
            date=date,
            weather_summary=lines[0] if lines else "Weather data unavailable",
            irrigation_summary=lines[1] if len(lines) > 1 else "",
            yield_outlook=lines[2] if len(lines) > 2 else "",
            alerts=[],  # Would parse from response
            tomorrow_plan=lines[-1] if lines else "",
        )
    
    def answer_question(
        self,
        question: str,
        farm_state: Dict[str, Any],
        recent_decisions: List[Dict[str, Any]] = None,
    ) -> str:
        """Answer a farmer's question about farm state or decisions."""
        
        prompt = ANSWER_QUESTION_PROMPT.format(
            question=question,
            farm_state=json.dumps(farm_state, indent=2, default=str),
            recent_decisions=json.dumps(recent_decisions or [], indent=2, default=str)[:1000],
        )
        
        return self.backend.complete(prompt, system=SYSTEM_PROMPT, max_tokens=300)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    # Test with Ollama (requires local Ollama running)
    print("Testing AgriMesh Explainer...")
    
    # Try Ollama first, fall back to mock
    try:
        backend = OllamaBackend("llama3")
        test_response = backend.complete("Say 'hello' in one word.")
        if "Error" in test_response:
            raise Exception("Ollama not available")
        print(f"Using Ollama backend")
    except:
        print("Ollama not available, using mock responses")
        
        class MockBackend(LLMBackend):
            def complete(self, prompt: str, system: str = None, max_tokens: int = 500) -> str:
                return "The irrigation was reduced because recent rainfall provided adequate moisture. Soil levels are healthy and crops are on track for expected yield."
        
        backend = MockBackend()
    
    explainer = AgriMeshExplainer(backend=backend)
    
    # Test decision explanation
    request = ExplanationRequest(
        cycle_id="test-001",
        decision_log={
            "rationale": "Rule-based irrigation; target=0.65; rain_factor=0.8; stress_plots=[]",
            "action_plan": {"irrigation_by_plot_liters": {"plot-1": 45.0, "plot-2": 30.0}},
        },
        outcome_log={
            "actual_changes": {
                "soil_moisture_before": {"plot-1": 0.52, "plot-2": 0.58},
                "soil_moisture_after": {"plot-1": 0.61, "plot-2": 0.65},
            },
            "kpi_delta": {
                "water_use_efficiency": 0.72,
                "yield_estimate_tons_per_ha": 4.8,
            },
        },
        farm_state_summary={"temperature_c": 28, "rainfall_mm": 5},
    )
    
    explanation = explainer.explain_decision(request)
    print(f"\n=== Decision Explanation ===")
    print(f"Summary: {explanation.summary}")
    print(f"Detail: {explanation.detailed}")
    
    # Test question answering
    answer = explainer.answer_question(
        question="Why is my maize looking yellow?",
        farm_state={"soil_moisture": 0.35, "last_irrigation": "2 days ago", "rainfall_last_week": 0},
    )
    print(f"\n=== Question Answer ===")
    print(answer)
