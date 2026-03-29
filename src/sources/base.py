"""
Abstract base class for all headline sources.

Any new source (Bloomberg, Reuters API, database, file, etc.) implements
this interface and plugs into KafkaProducerService without any other changes.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.core.models import Headline


class HeadlineSource(ABC):

    @abstractmethod
    async def connect(self):
        """Establish connection to the source."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Release the connection."""
        pass

    @abstractmethod
    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        """
        Yield Headline objects from the source.

        For finite sources (e.g. file), the generator terminates naturally.
        For continuous sources (e.g. KDB poll), it runs until disconnect() is called.
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        pass
