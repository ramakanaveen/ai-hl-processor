"""
Tests for RedisImpactStore using fakeredis (no real Redis needed).
"""
import asyncio
import time
import pytest
import fakeredis.aioredis as fakeredis

from src.memory.redis_store import RedisImpactStore, ActiveImpactEntry
from src.core.models import ImpactAnalysisResult, CurrencyImpact
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(headline: str, currencies=("GBP",), confidence=0.85) -> ImpactAnalysisResult:
    return ImpactAnalysisResult(
        headline=headline,
        timestamp=datetime.utcnow(),
        impacted_entities=[
            CurrencyImpact(currency=ccy, confidence=confidence, reasoning=f"test impact on {ccy}")
            for ccy in currencies
        ],
        processing_time_ms=10.0,
        model_used="test",
    )


async def _patched_store(monkeypatch) -> RedisImpactStore:
    """Return a RedisImpactStore whose internal redis client is a fakeredis instance."""
    store = RedisImpactStore(host="localhost", port=6379, ttl_seconds=3600)
    fake = fakeredis.FakeRedis(decode_responses=True)
    store._redis = fake
    store._available = True
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_miss_returns_none(monkeypatch):
    store = await _patched_store(monkeypatch)
    result = await store.get_cached_result("this headline was never stored")
    assert result is None


@pytest.mark.asyncio
async def test_cache_round_trip(monkeypatch):
    store = await _patched_store(monkeypatch)
    original = _make_result("Fed raises rates by 50bps", currencies=["USD", "GBP"])

    await store.cache_result(original)
    retrieved = await store.get_cached_result("Fed raises rates by 50bps")

    assert retrieved is not None
    assert retrieved.headline == original.headline
    assert len(retrieved.impacted_entities) == len(original.impacted_entities)
    currencies = {e.currency.value if hasattr(e.currency, "value") else e.currency
                  for e in retrieved.impacted_entities}
    assert "USD" in currencies
    assert "GBP" in currencies


@pytest.mark.asyncio
async def test_dedup_normalisation(monkeypatch):
    """Same headline with different casing/whitespace must map to the same key."""
    store = await _patched_store(monkeypatch)
    original = _make_result("Fed raises rates by 50bps")

    await store.cache_result(original)

    assert await store.get_cached_result("FED RAISES RATES BY 50BPS") is not None
    assert await store.get_cached_result("  fed raises rates by 50bps  ") is not None
    assert await store.get_cached_result("ECB cuts rates") is None


@pytest.mark.asyncio
async def test_impact_timeline_stored(monkeypatch):
    store = await _patched_store(monkeypatch)
    result = _make_result("UK unemployment rises", currencies=["GBP"])

    await store.store_impact_timeline(result)

    entries = await store.get_active_impacts(window_minutes=60)
    assert any(e.currency == "GBP" for e in entries)
    gbp_entries = [e for e in entries if e.currency == "GBP"]
    assert gbp_entries[0].headline == "UK unemployment rises"
    assert gbp_entries[0].confidence == pytest.approx(0.85, abs=0.01)


@pytest.mark.asyncio
async def test_active_impacts_time_window(monkeypatch):
    """Entries older than the window should not appear; recent ones should."""
    store = await _patched_store(monkeypatch)

    headline_hash = store._headline_hash("old headline")
    ccy = "USD"
    old_ts = time.time() - 7200  # 2 hours ago
    member = f"{headline_hash}:{ccy}"

    # Manually insert an old entry
    await store._redis.zadd(store._timeline_key(ccy), {member: old_ts})
    await store._redis.hset(store._impact_key(headline_hash, ccy), mapping={
        "headline": "old headline",
        "confidence": "0.80",
        "reasoning": "old",
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Also insert a recent entry via the normal path
    recent = _make_result("Recent Fed comment", currencies=["USD"])
    await store.store_impact_timeline(recent)

    entries_60m = await store.get_active_impacts(window_minutes=60)
    headlines_60m = {e.headline for e in entries_60m}

    assert "old headline" not in headlines_60m
    assert "Recent Fed comment" in headlines_60m


@pytest.mark.asyncio
async def test_idempotent_store(monkeypatch):
    """Storing the same result twice must not create duplicate sorted-set members."""
    store = await _patched_store(monkeypatch)
    result = _make_result("Trump signs trade deal", currencies=["USD", "CNY"])

    await store.store_impact_timeline(result)
    await store.store_impact_timeline(result)

    entries = await store.get_active_impacts(window_minutes=60)
    usd_entries = [e for e in entries if e.currency == "USD"]
    cny_entries = [e for e in entries if e.currency == "CNY"]

    # ZADD on same member just updates the score — should be exactly 1 entry each
    assert len(usd_entries) == 1
    assert len(cny_entries) == 1


@pytest.mark.asyncio
async def test_is_available_false_when_no_connection():
    """A store that was never connected should report unavailable."""
    store = RedisImpactStore(host="127.0.0.1", port=19999)
    assert await store.is_available() is False


@pytest.mark.asyncio
async def test_unavailable_store_does_not_raise(monkeypatch):
    """All public methods must be safe to call on an unavailable store."""
    store = RedisImpactStore(host="127.0.0.1", port=19999)
    # connect() should swallow the error and return False
    connected = await store.connect()
    assert connected is False
    assert await store.is_available() is False
