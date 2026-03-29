"""
Kafka feed adapter — consumes from the raw-headlines topic.

Implements FeedAdapter so HeadlineImpactAnalyzer requires zero changes.
Message envelope format matches what KafkaProducerService publishes:
  {
    "type": "headline",
    "timestamp": "<iso>",
    "data": { "text": "...", "source": "...", "timestamp": "...", "metadata": {} }
  }
"""
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from aiokafka import AIOKafkaConsumer

from src.feeds.base import FeedAdapter
from src.core.models import Headline

logger = logging.getLogger(__name__)


class KafkaFeedAdapter(FeedAdapter):

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self._consumer: AIOKafkaConsumer = None
        self._connected = False

    async def connect(self):
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="latest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._connected = True
        logger.info(f"KafkaFeedAdapter connected — broker={self.bootstrap_servers} topic={self.topic} group={self.group_id}")

    async def disconnect(self):
        if self._consumer:
            await self._consumer.stop()
        self._connected = False
        logger.info("KafkaFeedAdapter disconnected")

    async def is_connected(self) -> bool:
        return self._connected

    def _parse_message(self, data: dict) -> Headline | None:
        try:
            if data.get("type") != "headline":
                return None

            payload = data.get("data", {})
            text = payload.get("text", "").strip()
            if not text:
                return None

            ts_str = payload.get("timestamp") or payload.get("published")
            try:
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now()
            except (ValueError, AttributeError):
                timestamp = datetime.now()

            return Headline(
                text=text,
                source=payload.get("source", "kafka"),
                timestamp=timestamp,
                metadata=payload.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Failed to parse Kafka message: {e}")
            return None

    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        async for msg in self._consumer:
            headline = self._parse_message(msg.value)
            if headline:
                logger.info(f"Received from Kafka: {headline.text[:70]}...")
                yield headline
