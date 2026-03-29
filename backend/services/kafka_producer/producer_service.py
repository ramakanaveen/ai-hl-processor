"""
Kafka Producer Service

Source-agnostic: accepts any HeadlineSource implementation (FileSource,
KDBSource, or anything added later) and publishes headlines to a Kafka topic.
"""
import json
import logging
from datetime import datetime

from aiokafka import AIOKafkaProducer

from src.sources.base import HeadlineSource

logger = logging.getLogger(__name__)


class KafkaProducerService:

    def __init__(
        self,
        source: HeadlineSource,
        bootstrap_servers: str,
        topic: str,
    ):
        self.source = source
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: AIOKafkaProducer = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",              # wait for all in-sync replicas to confirm
            enable_idempotence=True, # exactly-once delivery per producer session
        )
        await self._producer.start()
        await self.source.connect()

        source_name = type(self.source).__name__
        logger.info(f"KafkaProducerService started — source={source_name} topic={self.topic}")

        try:
            async for headline in self.source.stream_headlines():
                message = {
                    "type": "headline",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "text": headline.text,
                        "source": headline.source,
                        "timestamp": headline.timestamp.isoformat(),
                        "metadata": headline.metadata,
                    },
                }
                await self._producer.send(self.topic, message)
                logger.info(f"Published → {self.topic}: {headline.text[:70]}...")

        finally:
            await self._producer.stop()
            await self.source.disconnect()
            logger.info("KafkaProducerService stopped")
