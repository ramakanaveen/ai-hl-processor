"""
RSS Feed Poller
Polls RSS feeds, deduplicates headlines, and publishes to input WebSocket server
"""
import asyncio
import feedparser
import websockets
import json
import hashlib
import yaml
import os
import ssl
from datetime import datetime
from typing import Set, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Handle SSL certificates for macOS
# feedparser uses urllib which respects this setting
try:
    import certifi
    # Create a function that returns the SSL context
    def create_ssl_context():
        return ssl.create_default_context(cafile=certifi.where())
    ssl._create_default_https_context = create_ssl_context
except ImportError:
    # Fallback: disable SSL verification (not recommended for production)
    logger.warning("certifi not found, using unverified SSL context")
    ssl._create_default_https_context = ssl._create_unverified_context


class RSSFeedPoller:
    """
    RSS Feed Poller that:
    - Polls multiple RSS feeds at configurable intervals
    - Deduplicates headlines using hash-based tracking
    - Publishes new headlines to WebSocket server
    - Handles errors and reconnection
    """

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.logger = logging.getLogger(__name__)
        self.seen_headlines: Set[str] = set()
        self.load_seen_headlines()

    def load_seen_headlines(self):
        """Load seen headlines from persistent storage"""
        seen_file = Path(self.config['deduplication']['file_path'])
        if seen_file.exists():
            try:
                with open(seen_file) as f:
                    data = json.load(f)
                    self.seen_headlines = set(data.keys())
                    self.logger.info(f"Loaded {len(self.seen_headlines)} seen headlines from {seen_file}")
            except Exception as e:
                self.logger.error(f"Error loading seen headlines: {e}")
                self.seen_headlines = set()
        else:
            self.logger.info("No existing seen headlines file, starting fresh")

    def save_seen_headlines(self):
        """Save seen headlines to persistent storage"""
        seen_file = Path(self.config['deduplication']['file_path'])
        try:
            # Ensure parent directory exists
            seen_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                guid: {"first_seen": datetime.now().isoformat()}
                for guid in self.seen_headlines
            }
            with open(seen_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving seen headlines: {e}")

    def generate_guid(self, title: str, link: str) -> str:
        """Generate unique ID for headline using SHA256 hash"""
        content = f"{title}|{link}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def poll_feed(self, feed_config: dict) -> list:
        """
        Poll single RSS feed and return new headlines

        Args:
            feed_config: Feed configuration with name, url, poll_interval_seconds

        Returns:
            List of new headline messages ready to publish
        """
        try:
            # Parse RSS feed (feedparser handles network request)
            feed = feedparser.parse(feed_config['url'])

            if feed.bozo:
                self.logger.warning(f"RSS parse warning for {feed_config['name']}: {feed.bozo_exception}")

            new_headlines = []

            for entry in feed.entries:
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()

                if not title or not link:
                    continue

                guid = self.generate_guid(title, link)

                # Check if we've seen this headline before
                if guid not in self.seen_headlines:
                    self.seen_headlines.add(guid)

                    # Create structured headline message
                    headline = {
                        "type": "headline",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "text": title,
                            "source": feed_config['name'],
                            "link": link,
                            "published": entry.get('published', datetime.now().isoformat()),
                            "guid": guid,
                            "metadata": {
                                "author": entry.get('author', 'Unknown'),
                                "summary": entry.get('summary', '')[:500]  # Limit summary length
                            }
                        }
                    }
                    new_headlines.append(headline)

            if new_headlines:
                self.logger.info(f"Found {len(new_headlines)} new headline(s) from {feed_config['name']}")
            else:
                self.logger.debug(f"No new headlines from {feed_config['name']}")

            return new_headlines

        except Exception as e:
            self.logger.error(f"Error polling {feed_config['name']}: {e}")
            return []

    async def publish_headlines(self, headlines: list):
        """
        Publish headlines to WebSocket server

        Args:
            headlines: List of headline messages to publish
        """
        if not headlines:
            return

        ws_url = self.config['websocket']['url']
        reconnect_interval = self.config['websocket'].get('reconnect_interval_seconds', 5)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with websockets.connect(ws_url) as websocket:
                    for headline in headlines:
                        await websocket.send(json.dumps(headline))
                        self.logger.info(f"Published: {headline['data']['text'][:60]}...")

                return  # Success

            except websockets.exceptions.WebSocketException as e:
                self.logger.warning(f"WebSocket error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(reconnect_interval)
            except Exception as e:
                self.logger.error(f"Error publishing to WebSocket: {e}")
                break

    async def run(self):
        """Main polling loop"""
        self.logger.info("Starting RSS Feed Poller...")
        self.logger.info(f"Polling {len(self.config['feeds'])} feed(s)")

        while True:
            for feed_config in self.config['feeds']:
                self.logger.info(f"Polling {feed_config['name']}...")

                # Poll feed
                headlines = await self.poll_feed(feed_config)

                # Publish new headlines
                if headlines:
                    await self.publish_headlines(headlines)
                    self.save_seen_headlines()

                # Wait before next poll of this feed
                await asyncio.sleep(feed_config['poll_interval_seconds'])


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    poller = RSSFeedPoller()
    asyncio.run(poller.run())
