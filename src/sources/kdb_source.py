"""
KDB+ headline source using qpython.

Polls KDB+ on a configurable interval using a q query and deduplicates
results by SHA-256 hash of (headline text + source) so restarts don't
re-emit headlines already published to Kafka.

Expected query result columns: text, source, time (or timestamp)
"""
import asyncio
import hashlib
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional, Set

from src.sources.base import HeadlineSource
from src.core.models import Headline

logger = logging.getLogger(__name__)


class KDBSource(HeadlineSource):

    def __init__(
        self,
        host: str,
        port: int,
        query: str,
        poll_interval_seconds: int = 60,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.query = query
        self.poll_interval_seconds = poll_interval_seconds
        self.username = username
        self.password = password
        self._connection = None
        self._connected = False
        self._seen: Set[str] = set()

    async def connect(self):
        try:
            import qpython.qconnection as qconn

            kwargs = {"host": self.host, "port": self.port}
            if self.username:
                kwargs["username"] = self.username
            if self.password:
                kwargs["password"] = self.password

            self._connection = qconn.QConnection(**kwargs)
            # QConnection.open() is synchronous — run in executor to avoid blocking the event loop
            await asyncio.get_event_loop().run_in_executor(None, self._connection.open)
            self._connected = True
            logger.info(f"KDBSource connected: {self.host}:{self.port}")

        except ImportError:
            raise RuntimeError("qpython is not installed. Run: pip install qpython")
        except Exception as e:
            logger.error(f"KDB+ connection failed: {e}")
            raise ConnectionError(f"Could not connect to KDB+ at {self.host}:{self.port}: {e}")

    async def disconnect(self):
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connected = False
        logger.info("KDBSource disconnected")

    async def is_connected(self) -> bool:
        return self._connected

    def _dedup_key(self, text: str, source: str) -> str:
        return hashlib.sha256(f"{text}{source}".encode()).hexdigest()[:16]

    def _run_query(self):
        """Synchronous KDB+ query — called via run_in_executor."""
        return self._connection(self.query)

    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        while self._connected:
            try:
                result = await asyncio.get_event_loop().run_in_executor(None, self._run_query)

                for row in result:
                    text = str(row["text"]).strip()
                    if not text:
                        continue

                    source = str(row.get("source", "kdb")).strip() or "kdb"
                    key = self._dedup_key(text, source)

                    if key in self._seen:
                        continue
                    self._seen.add(key)

                    raw_ts = row.get("time") or row.get("timestamp")
                    try:
                        timestamp = datetime.fromisoformat(str(raw_ts)) if raw_ts else datetime.now()
                    except (ValueError, TypeError):
                        timestamp = datetime.now()

                    yield Headline(text=text, source=source, timestamp=timestamp)

            except Exception as e:
                logger.error(f"KDB+ query error: {e}")

            await asyncio.sleep(self.poll_interval_seconds)
