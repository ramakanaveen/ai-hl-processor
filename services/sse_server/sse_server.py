"""
SSE Server

Consumes the headline-impacts Kafka topic and streams every analysis result
to connected clients via Server-Sent Events.

Each client gets its own asyncio.Queue so a slow client never blocks others.
The Kafka consumer runs as a single background task shared across all clients.

Endpoints:
    GET /events   — SSE stream of analysis results
    GET /health   — health check + connected client count
"""
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)

# One queue per connected SSE client
_clients: Set[asyncio.Queue] = set()


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


def create_app(bootstrap_servers: str, topic: str, group_id: str = "sse-server") -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(
            _kafka_consumer_loop(bootstrap_servers, topic, group_id)
        )
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="Headline Impact SSE Server", lifespan=lifespan)

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
                        # SSE comment keeps the connection alive through proxies
                        yield {"comment": "keepalive"}
            finally:
                _clients.discard(queue)
                logger.info(f"SSE client disconnected ({len(_clients)} remaining)")

        return EventSourceResponse(generator())

    return app
