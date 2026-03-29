"""
Integration tests for HeadlineImpactAnalyzer + RedisImpactStore.

Uses fakeredis — no real Redis or LLM required.
"""
import pytest
import fakeredis.aioredis as fakeredis

from src.memory.redis_store import RedisImpactStore
from src.core.analyzer import HeadlineImpactAnalyzer
from src.memory.file_store import FileSystemMemory
from src.core.models import ImpactAnalysisResult, CurrencyImpact
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_impact_result(headline: str) -> ImpactAnalysisResult:
    return ImpactAnalysisResult(
        headline=headline,
        timestamp=datetime.utcnow(),
        impacted_entities=[CurrencyImpact(currency="USD", confidence=0.90, reasoning="test")],
        processing_time_ms=5.0,
        model_used="mock",
    )


def _mock_agent(headline: str) -> AsyncMock:
    """Return an agent that always returns a USD impact."""
    agent = AsyncMock()
    agent.ainvoke.return_value = {
        "output": {
            "impacted_currencies": [
                {"currency": "USD", "confidence": 0.90, "reasoning": "mock reasoning"}
            ]
        }
    }
    return agent


async def _patched_redis_store() -> RedisImpactStore:
    store = RedisImpactStore(host="localhost", port=6379, ttl_seconds=3600)
    store._redis = fakeredis.FakeRedis(decode_responses=True)
    store._available = True
    return store


def _memory(tmp_path) -> FileSystemMemory:
    return FileSystemMemory(base_path=str(tmp_path / "memory"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_call_stores_in_redis(tmp_path):
    """After analyzing a headline the result is written to Redis."""
    store = await _patched_redis_store()
    mem = _memory(tmp_path)
    agent = _mock_agent("Fed raises rates")

    config = MagicMock()
    config.model_config.model_name = "mock"

    analyzer = HeadlineImpactAnalyzer(agent, mem, None, config, redis_store=store)
    await analyzer.analyze_headline("Fed raises rates")

    cached = await store.get_cached_result("Fed raises rates")
    assert cached is not None
    assert cached.headline == "Fed raises rates"


@pytest.mark.asyncio
async def test_second_call_still_invokes_agent(tmp_path):
    """
    The LLM is always called (dedup doesn't skip it).
    On the second call the agent prompt will contain prior context
    (handled inside agent.py), but the analyzer itself always calls ainvoke.
    """
    store = await _patched_redis_store()
    mem = _memory(tmp_path)
    agent = _mock_agent("Fed raises rates")

    config = MagicMock()
    config.model_config.model_name = "mock"

    analyzer = HeadlineImpactAnalyzer(agent, mem, None, config, redis_store=store)

    await analyzer.analyze_headline("Fed raises rates")
    await analyzer.analyze_headline("Fed raises rates")

    assert agent.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_analyzer_works_without_redis(tmp_path):
    """When redis_store=None the analyzer must work normally."""
    mem = _memory(tmp_path)
    agent = _mock_agent("ECB cuts rates")

    config = MagicMock()
    config.model_config.model_name = "mock"

    analyzer = HeadlineImpactAnalyzer(agent, mem, None, config, redis_store=None)
    result = await analyzer.analyze_headline("ECB cuts rates")

    assert result is not None
    assert result.headline == "ECB cuts rates"
    assert len(result.impacted_entities) == 1


@pytest.mark.asyncio
async def test_impact_timeline_populated(tmp_path):
    """After analysis the currency timeline should contain the entry."""
    store = await _patched_redis_store()
    mem = _memory(tmp_path)
    agent = _mock_agent("BoJ intervenes in FX market")

    config = MagicMock()
    config.model_config.model_name = "mock"

    analyzer = HeadlineImpactAnalyzer(agent, mem, None, config, redis_store=store)
    await analyzer.analyze_headline("BoJ intervenes in FX market")

    active = await store.get_active_impacts(window_minutes=60)
    assert any(e.currency == "USD" for e in active)


@pytest.mark.asyncio
async def test_unavailable_redis_no_exception(tmp_path):
    """If Redis becomes unavailable mid-run the analyzer must not raise."""
    store = RedisImpactStore(host="127.0.0.1", port=19999)
    # Do NOT call connect() — store stays unavailable

    mem = _memory(tmp_path)
    agent = _mock_agent("Trump announces tariffs")

    config = MagicMock()
    config.model_config.model_name = "mock"

    analyzer = HeadlineImpactAnalyzer(agent, mem, None, config, redis_store=store)
    result = await analyzer.analyze_headline("Trump announces tariffs")

    assert result is not None
    assert result.error is None
