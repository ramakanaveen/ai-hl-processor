import asyncio
import hashlib
from datetime import datetime

import fakeredis.aioredis as fakeredis
import pytest
from fastapi.testclient import TestClient

from services.sse_server import sse_server
from src.core.models import CurrencyImpact, ImpactAnalysisResult
from src.memory.file_store import FileSystemMemory
from src.memory.redis_store import RedisImpactStore


async def _idle_consumer(*args, **kwargs):
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        return


def _make_result(headline: str) -> ImpactAnalysisResult:
    return ImpactAnalysisResult(
        headline=headline,
        timestamp=datetime.utcnow(),
        impacted_entities=[
            CurrencyImpact(
                currency="USD",
                confidence=0.9,
                reasoning="Existing canonical reasoning for USD",
            )
        ],
        processing_time_ms=9.0,
        model_used="test",
    )


async def _patched_redis_store() -> RedisImpactStore:
    store = RedisImpactStore(host="localhost", port=6379, ttl_seconds=3600)
    store._redis = fakeredis.FakeRedis(decode_responses=True)
    store._available = True
    store.connect = lambda: asyncio.sleep(0, result=True)
    store.close = lambda: asyncio.sleep(0)
    return store


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(sse_server, "_kafka_consumer_loop", _idle_consumer)

    file_store = FileSystemMemory(base_path=str(tmp_path / "memory"))
    file_store.store_analysis(_make_result("Fed raises rates"))

    redis_store = asyncio.run(_patched_redis_store())

    app = sse_server.create_app(
        bootstrap_servers="localhost:9092",
        topic="headline-impacts",
        redis_store=redis_store,
        file_store=file_store,
        environment="test",
    )
    return app


def test_post_correction_returns_full_hash_and_persists_canonical(app):
    with TestClient(app) as client:
        response = client.post("/api/corrections", json={
            "headline": "Fed raises rates",
            "original_entities": [{"currency": "USD", "confidence": 0.9, "reasoning": "orig reasoning"}],
            "corrected_entities": [
                {
                    "currency": "AUD",
                    "confidence": 0.7,
                    "reasoning": "Manual correction added valid AUD reasoning",
                }
            ],
            "correction_note": "operator adjusted",
            "corrected_by": "reviewer",
        })

        assert response.status_code == 200
        payload = response.json()
        expected_hash = hashlib.sha256("Fed raises rates".lower().strip().encode()).hexdigest()
        assert payload["correction_id"] == expected_hash
        assert payload["result"]["impacted_entities"][0]["currency"] == "AUD"

        lookup = client.get(f"/api/corrections/{expected_hash}")
        assert lookup.status_code == 200
        assert lookup.json()["corrected_entities"][0]["currency"] == "AUD"


def test_post_correction_rejects_invalid_payload_without_false_success(app):
    with TestClient(app) as client:
        response = client.post("/api/corrections", json={
            "headline": "Fed raises rates",
            "original_entities": [{"currency": "USD", "confidence": 0.9, "reasoning": "orig reasoning"}],
            "corrected_entities": [
                {
                    "currency": "AUD",
                    "confidence": 0.7,
                    "reasoning": "short",
                }
            ],
            "correction_note": "operator adjusted",
            "corrected_by": "reviewer",
        })

        assert response.status_code == 422
        assert "Invalid correction payload" in response.json()["detail"]
