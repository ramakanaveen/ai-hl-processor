"""
Combined Headline Analysis + SSE Server

Single process that:
  1. Consumes raw-headlines from Kafka
  2. Runs LLM impact analysis
  3. Publishes results to headline-impacts Kafka topic (for external consumers)
  4. Streams results directly to UI via SSE (no Kafka hop for internal clients)
  5. Serves REST API (history, insights, stats, corrections)

User corrections are republished to the output topic marked as
type=analysis_corrected so external consumers receive the adjusted result.

Endpoints:
    GET  /health                             — health check + connected client count
    GET  /events                             — SSE stream of analysis results
    GET  /api/history                        — paginated analysis history
    GET  /api/insights                       — active Redis currency impact graph
    GET  /api/stats                          — system metrics
    GET  /api/stats/throughput               — time-bucketed analysis counts
    POST /api/corrections                    — save user correction + republish to Kafka
    GET  /api/corrections/{headline_hash}    — fetch existing correction
"""
import asyncio
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

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
# Analyzer loop — replaces the old Kafka consumer loop
# ---------------------------------------------------------------------------

async def _process_message(
    msg,
    analyzer,
    producer: AIOKafkaProducer,
    output_topic: str,
    relevance_filter=None,
    relevance_mode: str = "off",
) -> str:
    """
    Process a single raw-headline message: optionally gate it through the
    relevance filter, then (unless dropped in enforce mode) run the LLM analysis
    and publish/broadcast the result.

    Returns an action label for observability/testing:
        "empty" | "filtered_enforce" | "filtered_shadow" | "analyzed"
    """
    payload = msg.value
    data = payload.get("data", payload)
    headline_text = (data.get("text") or data.get("headline", "")).strip()
    if not headline_text:
        return "empty"
    source = data.get("source") or "unknown"

    action = "analyzed"
    if relevance_filter is not None and relevance_filter.loaded:
        # Scoring is CPU-bound — keep it off the event loop.
        decision = await asyncio.to_thread(
            relevance_filter.evaluate, headline_text, source
        )
        if decision.decision == "DROP":
            enforced = relevance_mode == "enforce"
            event = {
                "type": "relevance_filtered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "headline": headline_text,
                    "source": source,
                    "prob_relevant": round(decision.prob, 4),
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "mode": relevance_mode,
                    "enforced": enforced,
                    "top_features": decision.top_features[:5],
                },
            }
            # Always emit (shadow AND enforce) so the gate is measurable/auditable.
            await producer.send(output_topic, event)
            await _broadcast_to_clients(event)
            logger.info(
                "relevance_filtered (%s) p=%.3f reason=%s :: %s",
                relevance_mode, decision.prob, decision.reason, headline_text[:80],
            )
            if enforced:
                return "filtered_enforce"
            # Shadow mode: fall through and still analyze, for measurement.
            action = "filtered_shadow"

    result = await analyzer.analyze_headline(headline_text)
    kafka_msg = {
        "type": "analysis_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": result.model_dump(),
    }
    await producer.send(output_topic, kafka_msg)
    await _broadcast_to_clients({
        "type": "analysis_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": result.model_dump(),
    })
    return action


async def _analyzer_loop(
    bootstrap_servers: str,
    input_topic: str,
    output_topic: str,
    consumer_group: str,
    analyzer,
    producer: AIOKafkaProducer,
    relevance_filter=None,
    relevance_mode: str = "off",
):
    """
    Consume raw-headlines, analyse each one, publish the result to the
    output Kafka topic, and broadcast directly to connected SSE clients.
    """
    consumer = AIOKafkaConsumer(
        input_topic,
        bootstrap_servers=bootstrap_servers,
        group_id=consumer_group,
        auto_offset_reset="latest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    await consumer.start()
    logger.info(
        f"Analyzer loop started — input={input_topic}, output={output_topic}, "
        f"relevance={relevance_mode}"
    )

    try:
        async for msg in consumer:
            await _process_message(
                msg, analyzer, producer, output_topic,
                relevance_filter, relevance_mode,
            )

    finally:
        await consumer.stop()
        logger.info("Analyzer loop stopped")


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
    input_topic: str,
    output_topic: str,
    consumer_group: str,
    analyzer,
    redis_store=None,
    file_store=None,
    environment: str = "dev",
    relevance_filter=None,
    relevance_mode: str = "off",
) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if redis_store is not None:
            await redis_store.connect()

        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
            enable_idempotence=True,
        )
        await producer.start()
        app.state.kafka_producer = producer

        task = asyncio.create_task(
            _analyzer_loop(
                bootstrap_servers, input_topic, output_topic,
                consumer_group, analyzer, producer,
                relevance_filter, relevance_mode,
            )
        )
        yield

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await producer.stop()
        if redis_store is not None:
            await redis_store.close()

    app = FastAPI(title="Headline Impact Server", lifespan=lifespan)

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
    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "connected_clients": len(_clients),
            "environment": environment,
        }

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
                grouped[ccy] = {
                    "currency": ccy, "events": [], "event_count": 0,
                    "max_confidence": 0.0, "avg_confidence": 0.0,
                    "latest_timestamp": "",
                }
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
            data["events"].sort(key=lambda x: x["timestamp"], reverse=True)
            currencies.append(data)

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
                try:
                    name = fp.stem
                    ts_str = "_".join(name.split("_")[:2])
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

            return {
                "buckets": [
                    {
                        "bucket": datetime.fromtimestamp(k, tz=timezone.utc).isoformat(),
                        "count": v,
                    }
                    for k, v in sorted(counts.items())
                ]
            }

        return await asyncio.to_thread(_compute)

    # -----------------------------------------------------------------------
    # Corrections — update canonical store, republish to Kafka, broadcast SSE
    # -----------------------------------------------------------------------

    @app.post("/api/corrections")
    async def post_correction(body: CorrectionRequest, request: Request):
        headline_hash = hashlib.sha256(
            body.headline.lower().strip().encode()
        ).hexdigest()

        if file_store is None:
            raise HTTPException(status_code=500, detail="Canonical file store is not configured")

        # 1. Update canonical file store
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

        # 2. Update Redis
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

        # 3. File audit trail
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

        correction_payload = {
            "type": "analysis_corrected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": canonical_result.model_dump(),
        }

        # 4. Republish to Kafka so external consumers receive the adjusted result
        producer: Optional[AIOKafkaProducer] = getattr(request.app.state, "kafka_producer", None)
        if producer is not None:
            try:
                await producer.send(output_topic, correction_payload)
                logger.info(f"Correction republished to {output_topic}: {body.headline[:60]}")
            except Exception as e:
                logger.error(f"Kafka correction republish failed: {e}")

        # 5. Broadcast to connected SSE clients
        await _broadcast_to_clients(correction_payload)

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

        if file_store is not None:
            data = await asyncio.to_thread(
                file_store.get_correction_by_hash, headline_hash
            )
            if data:
                return data

        raise HTTPException(status_code=404, detail="No correction found")

    return app
