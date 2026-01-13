"""
Base Feed Adapter Interface

Defines the contract for feed adapters that provide headlines to the analyzer.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator
from src.core.models import Headline


class FeedAdapter(ABC):
    """
    Abstract base class for feed adapters

    Feed adapters connect to various headline sources (RSS, WebSocket, Bloomberg, KDB, etc.)
    and provide a uniform interface for the analyzer to consume headlines.
    """

    @abstractmethod
    async def connect(self):
        """
        Establish connection to the feed source

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """
        Disconnect from the feed source
        """
        pass

    @abstractmethod
    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        """
        Stream headlines from the feed source

        Yields:
            Headline: Parsed headline objects

        Raises:
            ConnectionError: If connection lost and reconnection fails
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if currently connected to feed source

        Returns:
            bool: True if connected, False otherwise
        """
        pass
