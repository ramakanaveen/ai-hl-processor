"""
SSE Server + REST API

Consumes the headline-impacts Kafka topic and streams every analysis result
to connected clients via Server-Sent Events.

Each client gets its own asyncio.Queue so a slow client never blocks others.
The Kafka consumer runs as a single background task shared across all clients.

Endpoints:
    GET  /health                             — health check + connected client count
    GET  /events                             — SSE stream of analysis results
    GET  /api/history                        — paginated analysis history
    GET  /api/insights                       — active Redis currency impact graph
    GET  /api/stats                          — system metrics
    GET  /api/stats/throughput               — time-bucketed analysis counts
    POST /api/corrections                    — save user correction
    GET  /api/corrections/{headline_hash}    — fetch existing correction
"""
import asyncio
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)

# One queue per connected SSE client
_clients: Set[asyncio.Queue] = set()


async def _broadcast_to_clients(message: dict):
    """Best-effort fan-out of a JSON-serializable message to all SSE clients."""
    if not _clients:
        return

    payload = json.dumps(message, default=str)
    for queue in list(_clients):
        await queue.put(payload)


# ---------------------------------------------------------------------------
# Kafka consumer loop
# ---------------------------------------------------------------------------

async def _kafka_consumer_loop(bootstrap_servers: str, topic: str, group_id: str):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="latest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    await consumer.start()
    logger.info(f"SSE Kafka consumer started — topic={topic}")

    try:
        async for msg in consumer:
            if _clients:
                payload = json.dumps(msg.value, default=str)
                for queue in list(_clients):
                    await queue.put(payload)
    finally:
        await consumer.stop()
        logger.info("SSE Kafka consumer stopped")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CorrectionRequest(BaseModel):
    headline: str
    original_entities: list
    corrected_entities: list
    correction_note: str = ""
    corrected_by: str = "user"


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    bootstrap_servers: str,
    topic: str,
    group_id: str = "sse-server",
    redis_store=None,
    file_store=None,
    environment: str = "dev",
) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if redis_store is not None:
            await redis_store.connect()
        task = asyncio.create_task(
            _kafka_consumer_loop(bootstrap_servers, topic, group_id)
        )
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        if redis_store is not None:
            await redis_store.close()

    app = FastAPI(title="Headline Impact SSE Server", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Health + SSE
    # -----------------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {"status": "ok", "connected_clients": len(_clients)}

    @app.get("/events")
    async def events(request: Request):
        queue: asyncio.Queue = asyncio.Queue()
        _clients.add(queue)
        logger.info(f"SSE client connected ({len(_clients)} total)")

        async def generator():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        payload = await asyncio.wait_for(queue.get(), timeout=20.0)
                        yield {"data": payload}
                    except asyncio.TimeoutError:
                        yield {"comment": "keepalive"}
            finally:
                _clients.discard(queue)
                logger.info(f"SSE client disconnected ({len(_clients)} remaining)")

        return EventSourceResponse(generator())

    # -----------------------------------------------------------------------
    # History
    # -----------------------------------------------------------------------

    @app.get("/api/history")
    async def get_history(
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        if file_store is None:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}

        def _read():
            files = sorted(
                file_store.analyses_path.glob("*.json"), reverse=True
            )
            total = len(files)
            page = files[offset: offset + limit]
            items = []
            for fp in page:
                try:
                    with open(fp) as f:
                        items.append(json.load(f))
                except Exception:
                    pass
            return {"items": items, "total": total, "limit": limit, "offset": offset}

        return await asyncio.to_thread(_read)

    # -----------------------------------------------------------------------
    # Redis Insights
    # -----------------------------------------------------------------------

    @app.get("/api/insights")
    async def get_insights(window_minutes: int = Query(60, ge=1, le=1440)):
        if redis_store is None or not await redis_store.is_available():
            return {"window_minutes": window_minutes, "currencies": [], "redis_available": False}

        entries = await redis_store.get_active_impacts(window_minutes=window_minutes)

        grouped: dict = {}
        for e in entries:
            ccy = e.currency
            if ccy not in grouped:
                grouped[ccy] = {"currency": ccy, "events": [], "event_count": 0,
                                 "max_confidence": 0.0, "avg_confidence": 0.0,
                                 "latest_timestamp": ""}
            grouped[ccy]["events"].append({
                "headline": e.headline,
                "confidence": e.confidence,
                "reasoning": e.reasoning,
                "timestamp": e.timestamp,
            })

        currencies = []
        for ccy, data in grouped.items():
            confs = [ev["confidence"] for ev in data["events"]]
            data["event_count"] = len(data["events"])
            data["max_confidence"] = round(max(confs), 3)
            data["avg_confidence"] = round(sum(confs) / len(confs), 3)
            data["latest_timestamp"] = max(ev["timestamp"] for ev in data["events"])
            # newest first within each currency
            data["events"].sort(key=lambda x: x["timestamp"], reverse=True)
            currencies.append(data)

        # most active first
        currencies.sort(key=lambda x: (-x["event_count"], -x["max_confidence"]))

        return {"window_minutes": window_minutes, "currencies": currencies, "redis_available": True}

    # -----------------------------------------------------------------------
    # Stats
    # -----------------------------------------------------------------------

    @app.get("/api/stats")
    async def get_stats():
        result = {
            "total_analyses": 0,
            "oldest_analysis": None,
            "newest_analysis": None,
            "analyses_per_hour": 0.0,
            "active_sse_clients": len(_clients),
            "redis_available": redis_store is not None and await redis_store.is_available(),
            "environment": environment,
        }

        if file_store is not None:
            stats = await asyncio.to_thread(file_store.get_stats)
            result["total_analyses"] = stats["total_analyses"]
            result["oldest_analysis"] = stats["oldest_analysis"]
            result["newest_analysis"] = stats["newest_analysis"]

            if stats["oldest_analysis"] and stats["newest_analysis"]:
                try:
                    oldest = datetime.fromisoformat(stats["oldest_analysis"])
                    newest = datetime.fromisoformat(stats["newest_analysis"])
                    hours = max((newest - oldest).total_seconds() / 3600, 1)
                    result["analyses_per_hour"] = round(stats["total_analyses"] / hours, 2)
                except Exception:
                    pass

        return result

    @app.get("/api/stats/throughput")
    async def get_throughput(
        hours: int = Query(24, ge=1, le=168),
        bucket_minutes: int = Query(60, ge=5, le=1440),
    ):
        if file_store is None:
            return {"buckets": []}

        def _compute():
            now = datetime.now(timezone.utc)
            cutoff_ts = now.timestamp() - hours * 3600
            bucket_secs = bucket_minutes * 60

            counts: dict = {}
            for fp in file_store.analyses_path.glob("*.json"):
                # filename format: YYYYMMDD_HHMMSS_<hash>.json
                try:
                    name = fp.stem  # e.g. 20260326_143000_abc123
                    ts_str = "_".join(name.split("_")[:2])  # 20260326_143000
                    dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").replace(
                        tzinfo=timezone.utc
                    )
                    ts = dt.timestamp()
                    if ts < cutoff_ts:
                        continue
                    bucket_key = int(ts // bucket_secs) * bucket_secs
                    counts[bucket_key] = counts.get(bucket_key, 0) + 1
                except Exception:
                    pass

            buckets = [
                {
                    "bucket": datetime.fromtimestamp(k, tz=timezone.utc).isoformat(),
                    "count": v,
                }
                for k, v in sorted(counts.items())
            ]
            return {"buckets": buckets}

        return await asyncio.to_thread(_compute)

    # -----------------------------------------------------------------------
    # Corrections
    # -----------------------------------------------------------------------

    @app.post("/api/corrections")
    async def post_correction(body: CorrectionRequest):
        headline_hash = hashlib.sha256(
            body.headline.lower().strip().encode()
        ).hexdigest()
        canonical_result = None

        if file_store is None:
            raise HTTPException(status_code=500, detail="Canonical file store is not configured")

        try:
            updated_results = await asyncio.to_thread(
                file_store.apply_correction,
                body.headline,
                body.corrected_entities,
                body.correction_note,
                body.corrected_by,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Invalid correction payload: {e}") from e
        except Exception as e:
            logger.error(f"Canonical analysis update failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to update canonical analysis") from e

        if not updated_results:
            raise HTTPException(
                status_code=404,
                detail="No matching stored analysis found for this headline",
            )

        canonical_result = updated_results[0]

        # Redis primary
        if redis_store is not None and await redis_store.is_available():
            try:
                await redis_store.replace_result(canonical_result)
                await redis_store.store_correction(
                    headline=body.headline,
                    original_entities=body.original_entities,
                    corrected_entities=body.corrected_entities,
                    note=body.correction_note,
                    corrected_by=body.corrected_by,
                )
            except Exception as e:
                logger.error(f"Redis correction write failed: {e}")

        # File audit trail (best effort once canonical result is updated)
        try:
            await asyncio.to_thread(
                file_store.store_correction,
                body.headline,
                body.original_entities,
                body.corrected_entities,
                body.correction_note,
                body.corrected_by,
            )
        except Exception as e:
            logger.error(f"File correction write failed: {e}")

        await _broadcast_to_clients({
            "type": "analysis_corrected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": canonical_result.model_dump(),
        })

        return {
            "status": "saved",
            "correction_id": headline_hash,
            "result": canonical_result.model_dump(),
        }

    @app.get("/api/corrections/{headline_hash}")
    async def get_correction(headline_hash: str):
        if redis_store is not None and await redis_store.is_available():
            data = await redis_store.get_correction_by_hash(headline_hash)
            if data:
                return data

        # Fall back to file scan
        if file_store is not None:
            data = await asyncio.to_thread(
                file_store.get_correction_by_hash, headline_hash
            )
            if data:
                return data

        raise HTTPException(status_code=404, detail="No correction found")

    return app
