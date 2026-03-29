
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from langchain_core.agents import AgentFinish
from src.memory.file_store import FileSystemMemory
from src.memory.tools import create_memory_tools
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt context builders (module-level so they are easily testable)
# ---------------------------------------------------------------------------

def _build_prior_analysis_context(prior) -> str:
    """
    Format a previously cached ImpactAnalysisResult as a prompt section.
    Injected when the same headline has been analysed before.
    """
    try:
        ts = prior.timestamp
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        time_str = ts.strftime("%H:%M UTC")
    except Exception:
        time_str = "unknown time"

    lines = [f"\nPREVIOUS ANALYSIS OF THIS HEADLINE (seen at {time_str}):"]
    for entity in prior.impacted_entities:
        ccy = entity.currency.value if hasattr(entity.currency, "value") else str(entity.currency)
        lines.append(f"  {ccy}: {entity.confidence:.2f} confidence — {entity.reasoning}")
    lines.append("Consider whether your current assessment confirms, strengthens, or revises this.")
    return "\n".join(lines)


def _build_active_impact_context(impacts: list, window_minutes: int) -> str:
    """
    Format the current currency impact graph as a prompt section.
    Currencies with recent events are listed first (most events → highest confidence).
    Currencies with no events are listed on a final summary line.
    """
    from src.memory.redis_store import _CURRENCIES

    # Group entries by currency
    by_currency: dict = defaultdict(list)
    for entry in impacts:
        by_currency[entry.currency].append(entry)

    # Sort currencies: most events first, then by max confidence
    sorted_currencies = sorted(
        by_currency.keys(),
        key=lambda c: (-len(by_currency[c]), -max(e.confidence for e in by_currency[c]))
    )

    lines = [f"\nACTIVE MARKET PRESSURES (last {window_minutes} minutes):\n"]
    for ccy in sorted_currencies:
        events = sorted(by_currency[ccy], key=lambda e: e.timestamp, reverse=True)
        lines.append(f"{ccy} ({len(events)} event{'s' if len(events) > 1 else ''}):")
        for ev in events:
            try:
                ts = datetime.fromisoformat(ev.timestamp)
                time_str = ts.strftime("%H:%M UTC")
            except Exception:
                time_str = "??:?? UTC"
            lines.append(f"  [{time_str}] conf={ev.confidence:.2f} | \"{ev.headline}\"")
            lines.append(f"              → {ev.reasoning}")
        lines.append("")

    quiet = [c for c in _CURRENCIES if c not in by_currency]
    if quiet:
        lines.append(f"No recent pressure on: {', '.join(quiet)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gemini agent
# ---------------------------------------------------------------------------

def create_impact_analysis_agent(config, memory: FileSystemMemory, redis_store=None):
    """
    Create LangChain agent for headline impact analysis with memory.
    Uses Gemini Flash via Vertex AI with memory context enrichment.
    """
    from langchain_google_vertexai import ChatVertexAI
    import os
    import json
    import warnings

    warnings.filterwarnings('ignore', category=DeprecationWarning, module='langchain_google_vertexai')
    from langchain_core._api import LangChainDeprecationWarning
    warnings.filterwarnings('ignore', category=LangChainDeprecationWarning)

    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        logger.info("Set GOOGLE_APPLICATION_CREDENTIALS from GOOGLE_CREDENTIALS_PATH")

    llm = ChatVertexAI(
        model_name=config.model_config.model_name,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_LOCATION", "us-central1"),
        temperature=config.model_config.temperature,
        max_output_tokens=config.model_config.max_tokens,
    )

    class GeminiAgentExecutor:
        """Custom agent executor that enriches prompts with file memory and Redis impact graph."""

        def __init__(self, llm, memory, config, redis_store=None):
            self.llm = llm
            self.memory = memory
            self.config = config
            self.redis_store = redis_store

        async def ainvoke(self, inputs: dict) -> dict:
            headline = inputs['input'].replace("Analyze this headline for currency impact: ", "")

            # --- File-based similarity context ---
            similar = self.memory.search_similar_headlines(headline, limit=3, similarity_threshold=0.4)
            memory_context = ""
            if similar:
                memory_context = "\n\nRELEVANT PAST ANALYSES:\n"
                for i, analysis in enumerate(similar, 1):
                    memory_context += f"\n{i}. \"{analysis.headline}\"\n"
                    memory_context += f"   Impacted: {', '.join(e.currency for e in analysis.impacted_entities)}\n"
                    for entity in analysis.impacted_entities:
                        memory_context += f"   - {entity.currency}: {entity.confidence:.2f} confidence - {entity.reasoning}\n"

            # --- Redis context (prior result + active impact graph) ---
            prior_context = ""
            active_context = ""
            if self.redis_store and await self.redis_store.is_available():
                prior = await self.redis_store.get_cached_result(headline)
                if prior is not None:
                    prior_context = _build_prior_analysis_context(prior)

                redis_cfg = self.config.get_redis_config()
                window = redis_cfg.get('active_impact_window_minutes', 60)
                active_impacts = await self.redis_store.get_active_impacts(window_minutes=window)
                if active_impacts:
                    active_context = _build_active_impact_context(active_impacts, window)

            system_prompt = """You are an expert financial analyst specializing in currency markets and foreign exchange (FX) trading.

Your task is to analyze news headlines and determine which currencies will be impacted by the news event.

Consider these factors:
1. Direct mentions of countries, central banks, or currencies
2. Economic relationships and trade dependencies
3. Market sentiment and safe-haven flows
4. Central bank policy implications
5. Geopolitical risk factors

If you are provided with a PREVIOUS ANALYSIS of this same headline, use it as a baseline and indicate
whether this event is still in play, strengthening, or changing direction.

If you are provided with ACTIVE MARKET PRESSURES, consider how this headline interacts with the
existing impacts — does it compound or relax existing pressure on a currency?

IMPORTANT: Return your response as valid JSON with this exact structure:
{
  "impacted_currencies": [
    {
      "currency": "GBP",
      "confidence": 0.85,
      "reasoning": "UK Chancellor fiscal policy directly impacts British pound"
    }
  ]
}

Supported currencies: USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD, CNY
Only include currencies with confidence >= 0.5. If no clear impact, return empty array."""

            user_prompt = f"""Analyze the following news headline for currency impact:

HEADLINE: "{headline}"{memory_context}{prior_context}{active_context}

Provide your analysis as JSON with impacted_currencies array."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.llm.ainvoke(messages)

            try:
                response_text = response.content

                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                if "{" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    response_text = response_text[json_start:json_end]

                result = json.loads(response_text)
                impacted = result.get("impacted_currencies", [])
                normalized = []
                for impact in impacted:
                    if isinstance(impact, dict) and "currency" in impact:
                        normalized.append({
                            "currency": impact["currency"],
                            "confidence": float(impact.get("confidence", 0.5)),
                            "reasoning": impact.get("reasoning", "No reasoning provided")
                        })

                return {"output": {"impacted_currencies": normalized}}

            except Exception as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                logger.debug(f"Raw response: {response.content}")
                return {"output": {"impacted_currencies": []}}

    return GeminiAgentExecutor(llm, memory, config, redis_store)


# ---------------------------------------------------------------------------
# Mock agent (test / dev)
# ---------------------------------------------------------------------------

def create_mock_agent(memory: FileSystemMemory, redis_store=None):
    """
    Mock agent for test/dev environments — keyword matching, no LLM calls.
    redis_store is accepted but not used (mock path has no async context injection).
    """
    def mock_agent_logic(inputs: dict) -> AgentFinish:
        headline = inputs['input'].lower()
        impacts = []

        if 'uk' in headline or 'britain' in headline or 'reeves' in headline:
            impacts.append({'currency': 'GBP', 'confidence': 0.85, 'reasoning': 'Mock: UK-related keywords detected'})
        if 'fed' in headline or 'us' in headline or 'powell' in headline or 'federal' in headline:
            impacts.append({'currency': 'USD', 'confidence': 0.90, 'reasoning': 'Mock: US/Fed-related keywords detected'})
        if 'ecb' in headline or 'europe' in headline or 'eu' in headline or 'european' in headline:
            impacts.append({'currency': 'EUR', 'confidence': 0.85, 'reasoning': 'Mock: EU/ECB-related keywords detected'})
        if 'japan' in headline or 'boj' in headline or 'yen' in headline:
            impacts.append({'currency': 'JPY', 'confidence': 0.80, 'reasoning': 'Mock: Japan/BOJ-related keywords detected'})
        if 'china' in headline or 'yuan' in headline or 'pboc' in headline:
            impacts.append({'currency': 'CNY', 'confidence': 0.80, 'reasoning': 'Mock: China-related keywords detected'})

        return AgentFinish(
            return_values={'output': {'impacted_currencies': impacts}},
            log="Mock agent execution completed"
        )

    class MockAgentExecutor:
        def __init__(self, agent_func):
            self.agent_func = agent_func

        async def ainvoke(self, inputs: dict) -> dict:
            result = self.agent_func(inputs)
            return result.return_values

    return MockAgentExecutor(mock_agent_logic)
