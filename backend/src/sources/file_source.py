"""
CSV file headline source with rate limiting.

Expected CSV columns: headline, source, timestamp
  - headline:  the news headline text (required)
  - source:    publisher name (optional, defaults to "file")
  - timestamp: ISO-8601 datetime (optional, defaults to now)
"""
import csv
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator

from src.sources.base import HeadlineSource
from src.core.models import Headline

logger = logging.getLogger(__name__)


class FileSource(HeadlineSource):

    def __init__(self, file_path: str, rate_limit_per_second: float = 1.0):
        self.file_path = file_path
        self.rate_limit_per_second = rate_limit_per_second
        self._connected = False

    async def connect(self):
        self._connected = True
        logger.info(f"FileSource ready: {self.file_path} @ {self.rate_limit_per_second}/s")

    async def disconnect(self):
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        interval = 1.0 / self.rate_limit_per_second

        try:
            with open(self.file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    text = row.get("headline", "").strip()
                    if not text:
                        continue

                    source = row.get("source", "file").strip() or "file"

                    timestamp_str = row.get("timestamp", "").strip()
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
                    except ValueError:
                        timestamp = datetime.now()

                    yield Headline(text=text, source=source, timestamp=timestamp)
                    await asyncio.sleep(interval)

        except FileNotFoundError:
            logger.error(f"CSV file not found: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise
