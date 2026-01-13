"""
WebSocket Feed Adapter

Connects to WebSocket server and streams headlines to the analyzer.
"""
import websockets
import json
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator
from src.feeds.base import FeedAdapter
from src.core.models import Headline

logger = logging.getLogger(__name__)


class WebSocketFeedAdapter(FeedAdapter):
    """
    WebSocket feed adapter - connects to input WebSocket server

    This adapter subscribes to a WebSocket server that broadcasts headlines
    from various sources (RSS, Bloomberg, KDB, etc.). It handles connection
    lifecycle, reconnection on failures, and converts WebSocket messages
    to Headline objects.
    """

    def __init__(
        self,
        url: str,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = -1  # -1 = infinite
    ):
        """
        Initialize WebSocket feed adapter

        Args:
            url: WebSocket server URL (e.g., "ws://localhost:8765")
            reconnect_interval: Seconds to wait between reconnection attempts
            max_reconnect_attempts: Max reconnection attempts (-1 = infinite)
        """
        self.url = url
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connection = None
        self._connected = False
        self._reconnect_count = 0

    async def connect(self):
        """
        Connect to WebSocket server

        Raises:
            ConnectionError: If initial connection fails after max attempts
        """
        try:
            self.connection = await websockets.connect(self.url)
            self._connected = True
            self._reconnect_count = 0
            logger.info(f"✓ Connected to WebSocket feed: {self.url}")

        except Exception as e:
            logger.error(f"✗ Failed to connect to WebSocket: {e}")
            self._connected = False
            raise ConnectionError(f"Could not connect to {self.url}: {e}")

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.connection:
            try:
                await self.connection.close()
                logger.info(f"Disconnected from WebSocket feed: {self.url}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self.connection = None

    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect to WebSocket server

        Returns:
            bool: True if reconnection successful, False otherwise
        """
        if self.max_reconnect_attempts >= 0 and self._reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return False

        self._reconnect_count += 1
        logger.warning(
            f"Reconnecting to WebSocket (attempt {self._reconnect_count})... "
            f"waiting {self.reconnect_interval}s"
        )

        await asyncio.sleep(self.reconnect_interval)

        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection attempt {self._reconnect_count} failed: {e}")
            return False

    def _parse_message(self, message: str) -> Headline | None:
        """
        Parse WebSocket message into Headline object

        Args:
            message: JSON string from WebSocket

        Returns:
            Headline object or None if invalid/non-headline message
        """
        try:
            data = json.loads(message)

            # Handle different message types
            message_type = data.get('type')

            if message_type == 'headline':
                headline_data = data.get('data', {})

                # Parse timestamp
                timestamp_str = headline_data.get('published') or headline_data.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()

                # Create Headline object
                return Headline(
                    text=headline_data.get('text', ''),
                    source=headline_data.get('source', 'websocket'),
                    timestamp=timestamp,
                    metadata={
                        'link': headline_data.get('link'),
                        'guid': headline_data.get('guid'),
                        'author': headline_data.get('metadata', {}).get('author'),
                        'summary': headline_data.get('metadata', {}).get('summary'),
                        'raw_message': data  # Keep full message for debugging
                    }
                )

            elif message_type == 'heartbeat':
                logger.debug("Received heartbeat from WebSocket server")
                return None

            else:
                logger.warning(f"Unknown message type: {message_type}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
            return None

        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
            return None

        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None

    async def stream_headlines(self) -> AsyncGenerator[Headline, None]:
        """
        Stream headlines from WebSocket

        Yields:
            Headline: Parsed headline objects

        This method handles:
        - Connection lifecycle
        - Automatic reconnection on failures
        - Message parsing and validation
        - Filtering non-headline messages
        """
        while True:
            try:
                # Ensure connected
                if not self.connection or not await self.is_connected():
                    if not await self._reconnect():
                        logger.error("Could not reconnect to WebSocket, stopping stream")
                        break

                # Stream messages
                async for message in self.connection:
                    headline = self._parse_message(message)

                    if headline and headline.text:
                        logger.info(f"📰 Received headline: {headline.text[:60]}...")
                        yield headline
                    else:
                        logger.debug("Skipped non-headline or empty message")

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self._connected = False

                # Try to reconnect
                if not await self._reconnect():
                    logger.error("Reconnection failed, stopping stream")
                    break

            except Exception as e:
                logger.error(f"Error in headline stream: {e}")
                self._connected = False

                # Try to reconnect
                await asyncio.sleep(self.reconnect_interval)
                if not await self._reconnect():
                    logger.error("Reconnection failed after error, stopping stream")
                    break

    async def is_connected(self) -> bool:
        """
        Check if currently connected to WebSocket server

        Returns:
            bool: True if connected and connection is open
        """
        if not self._connected or self.connection is None:
            return False

        # Check if connection is still open
        # In websockets 15.0+, check the state attribute
        try:
            return hasattr(self.connection, 'open') and self.connection.open
        except AttributeError:
            # Fallback: assume connected if no exception
            return self._connected
