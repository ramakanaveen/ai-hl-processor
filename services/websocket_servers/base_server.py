"""
Base WebSocket Server
Provides core functionality for broadcasting messages to multiple clients
"""
import asyncio
import websockets
import json
import logging
from typing import Set
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class BaseWebSocketServer:
    """Base WebSocket server with broadcast capabilities"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client connection"""
        self.clients.add(websocket)
        self.logger.info(f"Client connected from {websocket.remote_address}. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client connection"""
        self.clients.discard(websocket)
        self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.clients:
            self.logger.warning("No clients connected to broadcast to")
            return

        message_json = json.dumps(message)
        disconnected = set()

        # Send to all clients
        for websocket in self.clients:
            try:
                await websocket.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                self.logger.error(f"Error sending to client: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unregister(websocket)

        if disconnected:
            self.logger.info(f"Removed {len(disconnected)} disconnected client(s)")

    async def handler(self, websocket):
        """Handle WebSocket connection lifecycle"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    # Parse and broadcast message
                    data = json.loads(message)
                    await self.broadcast(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.debug("Connection closed normally")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            await self.unregister(websocket)

    async def start(self):
        """Start WebSocket server"""
        self.logger.info(f"Starting {self.__class__.__name__} on {self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            self.logger.info(f"Server ready and listening")
            await asyncio.Future()  # Run forever
