#!/usr/bin/env python3
"""
Run RSS Feed Poller
Entry point for starting the RSS feed polling service
"""
import asyncio
import logging
from rss_feed_poller import RSSFeedPoller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Start the RSS feed poller"""
    try:
        poller = RSSFeedPoller()
        logger.info("RSS Feed Poller starting...")
        await poller.run()

    except KeyboardInterrupt:
        logger.info("Poller stopped by user")
    except Exception as e:
        logger.error(f"Poller error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
