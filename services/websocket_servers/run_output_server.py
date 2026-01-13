#!/usr/bin/env python3
"""
Run Output WebSocket Server
Entry point for starting the output WebSocket server (results bus)
"""
import asyncio
import logging
import yaml
from output_server import OutputWebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Start the output WebSocket server"""
    try:
        # Load configuration
        with open("output_config.yaml") as f:
            config = yaml.safe_load(f)

        # Set log level from config
        log_level = getattr(logging, config['logging']['level'])
        logging.getLogger().setLevel(log_level)

        # Create and start server
        server = OutputWebSocketServer(
            host=config['server']['host'],
            port=config['server']['port']
        )

        logger.info("Output WebSocket Server starting...")
        await server.start()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
