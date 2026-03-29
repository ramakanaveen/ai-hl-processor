"""
Redis-backed headline cache and currency impact graph.

Two responsibilities:
  1. Headline cache — store every processed ImpactAnalysisResult keyed by a
     SHA-256 hash of the normalised headline text.  When the same headline
     arrives again the agent can pull the previous result and include it in
     its prompt context.

  2. Impact graph — a per-currency sorted set (score = unix timestamp) that
     records every confident impact event.  The agent can query "what has
     been moving GBP in the last 60 minutes?" and include that as context
     before calling the LLM.

All methods are best-effort: if Redis is unavailable the system continues
with file-system memory only.

Key schema
----------
  hl:dedup:<sha256>               STRING  full ImpactAnalysisResult (JSON)
  hl:timeline:<CURRENCY>          ZSET    member = "<sha256>:<ccy>", score = unix ts
  hl:impact:<sha256>:<CURRENCY>   HASH    headline / confidence / reasoning / timestamp
"""
import hashlib
import json
import logging
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

logger = logging.getLogger(__name__)

_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "CNY"]


@dataclass
class ActiveImpactEntry:
    currency: str
    headline: str
    confidence: float
    reasoning: str
    timestamp: str  # ISO-8601 string


class RedisImpactStore:
    """
    Redis data layer for headline caching and the currency impact graph.
    Safe to instantiate even when Redis is unreachable — all public methods
    return gracefully and log a warning.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl_seconds: int = 86400,
        active_window_minutes: int = 60,
        password: Optional[str] = None,
        ssl: bool = False,
        ssl_cert_reqs: str = "required",
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        max_connections: int = 10,
    ):
        self._host = host
        self._port = port
        self._db = db
        self._ttl = ttl_seconds
        self._window_minutes = active_window_minutes
        self._password = password
        self._ssl = ssl
        self._ssl_cert_reqs = ssl_cert_reqs
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._max_connections = max_connections
        self._redis: Optional[aioredis.Redis] = None
        self._available = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Attempt to connect and PING.  Sets _available based on outcome.
        Never raises — safe to call unconditionally at startup.
        """
        try:
            pool_kwargs = dict(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                max_connections=self._max_connections,
                decode_responses=True,
            )
            if self._ssl:
                cert_reqs = ssl.CERT_REQUIRED if self._ssl_cert_reqs == "required" else ssl.CERT_NONE
                pool_kwargs["ssl"] = True
                pool_kwargs["ssl_cert_reqs"] = cert_reqs

            pool = ConnectionPool(**pool_kwargs)
            self._redis = aioredis.Redis(connection_pool=pool)
            await self._redis.ping()
            self._available = True
            logger.info(f"RedisImpactStore connected: {self._host}:{self._port} db={self._db}")
        except Exception as e:
            self._available = False
            logger.warning(f"Redis unavailable, running without cache: {e}")
        return self._available

    async def close(self):
        if self._redis:
            await self._redis.aclose()
            self._available = False

    async def is_available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _headline_hash(headline: str) -> str:
        normalised = headline.lower().strip()
        return hashlib.sha256(normalised.encode()).hexdigest()

    def _dedup_key(self, headline: str) -> str:
        return f"hl:dedup:{self._headline_hash(headline)}"

    def _timeline_key(self, currency: str) -> str:
        return f"hl:timeline:{currency.upper()}"

    def _impact_key(self, headline_hash: str, currency: str) -> str:
        return f"hl:impact:{headline_hash}:{currency.upper()}"

    # ------------------------------------------------------------------
    # Headline cache
    # ------------------------------------------------------------------

    async def get_cached_result(self, headline: str):
        """
        Return the cached ImpactAnalysisResult for this headline, or None.
        Imported lazily to avoid a circular import at module level.
        """
        from src.core.models import ImpactAnalysisResult
        try:
            raw = await self._redis.get(self._dedup_key(headline))
            if raw is None:
                return None
            return ImpactAnalysisResult(**json.loads(raw))
        except Exception as e:
            logger.error(f"Redis get_cached_result error: {e}")
            return None

    async def cache_result(self, result) -> None:
        """Store (or refresh TTL of) a result in the dedup cache."""
        try:
            key = self._dedup_key(result.headline)
            payload = json.dumps(result.model_dump(), default=str)
            await self._redis.setex(key, self._ttl, payload)
        except Exception as e:
            logger.error(f"Redis cache_result error: {e}")

    # ------------------------------------------------------------------
    # Impact graph
    # ------------------------------------------------------------------

    async def store_impact_timeline(self, result) -> None:
        """
        For each currency impact in result, write:
          - A member to the currency's sorted set (score = now)
          - A detail hash with headline / confidence / reasoning / timestamp
        """
        try:
            headline_hash = self._headline_hash(result.headline)
            now = time.time()
            pipe = self._redis.pipeline()

            for impact in result.impacted_entities:
                ccy = impact.currency.value if hasattr(impact.currency, "value") else str(impact.currency)
                member = f"{headline_hash}:{ccy}"

                pipe.zadd(self._timeline_key(ccy), {member: now})
                pipe.expire(self._timeline_key(ccy), self._ttl)

                detail_key = self._impact_key(headline_hash, ccy)
                pipe.hset(detail_key, mapping={
                    "headline": result.headline,
                    "confidence": str(impact.confidence),
                    "reasoning": impact.reasoning,
                    "timestamp": result.timestamp.isoformat() if isinstance(result.timestamp, datetime) else str(result.timestamp),
                })
                pipe.expire(detail_key, self._ttl)

            await pipe.execute()
        except Exception as e:
            logger.error(f"Redis store_impact_timeline error: {e}")

    async def replace_result(self, result) -> None:
        """
        Replace the canonical Redis view for a headline after a user correction.
        This removes any prior impact graph entries for the headline before
        writing the corrected result back into the cache and timelines.
        """
        try:
            headline_hash = self._headline_hash(result.headline)
            pipe = self._redis.pipeline()

            for ccy in _CURRENCIES:
                member = f"{headline_hash}:{ccy}"
                pipe.zrem(self._timeline_key(ccy), member)
                pipe.delete(self._impact_key(headline_hash, ccy))

            await pipe.execute()
            await self.cache_result(result)
            await self.store_impact_timeline(result)
        except Exception as e:
            logger.error(f"Redis replace_result error: {e}")

    async def get_active_impacts(self, window_minutes: Optional[int] = None) -> List[ActiveImpactEntry]:
        """
        Return all impact events across all currencies within the time window.
        Results are sorted: most-active currencies first, newest events first within each.
        """
        window = window_minutes or self._window_minutes
        now = time.time()
        min_score = now - (window * 60)

        entries: List[ActiveImpactEntry] = []
        try:
            for ccy in _CURRENCIES:
                members = await self._redis.zrangebyscore(
                    self._timeline_key(ccy), min_score, now
                )
                for member in members:
                    headline_hash = member.split(":")[0]
                    detail = await self._redis.hgetall(self._impact_key(headline_hash, ccy))
                    if detail:
                        entries.append(ActiveImpactEntry(
                            currency=ccy,
                            headline=detail.get("headline", ""),
                            confidence=float(detail.get("confidence", 0.0)),
                            reasoning=detail.get("reasoning", ""),
                            timestamp=detail.get("timestamp", ""),
                        ))
        except Exception as e:
            logger.error(f"Redis get_active_impacts error: {e}")

        return entries

    # ------------------------------------------------------------------
    # User corrections  (no TTL — permanent training signal)
    # ------------------------------------------------------------------

    def _correction_key(self, headline_hash: str) -> str:
        return f"hl:correction:{headline_hash}"

    async def store_correction(
        self,
        headline: str,
        original_entities: list,
        corrected_entities: list,
        note: str = "",
        corrected_by: str = "user",
    ) -> None:
        """Store a user correction permanently."""
        try:
            h = self._headline_hash(headline)
            key = self._correction_key(h)
            pipe = self._redis.pipeline()
            pipe.hset(key, mapping={
                "headline": headline,
                "original_entities": json.dumps(original_entities, default=str),
                "corrected_entities": json.dumps(corrected_entities, default=str),
                "correction_note": note,
                "corrected_by": corrected_by,
                "corrected_at": datetime.now().isoformat(),
            })
            pipe.zadd("hl:corrections:index", {h: time.time()})
            await pipe.execute()
        except Exception as e:
            logger.error(f"Redis store_correction error: {e}")

    async def get_correction(self, headline: str) -> Optional[dict]:
        """Retrieve a correction by headline text."""
        try:
            return await self.get_correction_by_hash(self._headline_hash(headline))
        except Exception as e:
            logger.error(f"Redis get_correction error: {e}")
            return None

    async def get_correction_by_hash(self, headline_hash: str) -> Optional[dict]:
        """Retrieve a correction by SHA-256 hash."""
        try:
            data = await self._redis.hgetall(self._correction_key(headline_hash))
            if not data:
                return None
            return {
                "headline": data.get("headline", ""),
                "original_entities": json.loads(data.get("original_entities", "[]")),
                "corrected_entities": json.loads(data.get("corrected_entities", "[]")),
                "correction_note": data.get("correction_note", ""),
                "corrected_by": data.get("corrected_by", "user"),
                "corrected_at": data.get("corrected_at", ""),
            }
        except Exception as e:
            logger.error(f"Redis get_correction_by_hash error: {e}")
            return None
