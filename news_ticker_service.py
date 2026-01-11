"""
Bloomberg-Style News Ticker Service
Continuously monitors news sources, analyzes headlines, and broadcasts to all connected clients
"""

import asyncio
import requests
import feedparser
from datetime import datetime
import json
import logging
import os
from typing import Set, List, Dict, Any
import websocket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsTickerService:
    """Production news ticker with queue-based processing and WebSocket broadcasting"""

    def __init__(self, newsapi_key: str = None, analyzer_url: str = "http://localhost:8000"):
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        self.analyzer_url = analyzer_url
        self.broadcast_url = analyzer_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/broadcast"
        self.seen_headlines: Set[str] = set()
        self.news_queue = asyncio.Queue()
        self.stats = {
            "total_headlines": 0,
            "analyzed": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        # RSS Feed URLs
        self.rss_feeds = [
            ("Reuters Business", "http://feeds.reuters.com/reuters/businessNews"),
            ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
            ("Bloomberg", "https://www.bloomberg.com/politics/feeds/site.xml"),
        ]

    async def monitor_newsapi(self, interval: int = 300, max_results: int = 20):
        """Monitor NewsAPI for new headlines and add to queue"""
        if not self.newsapi_key:
            logger.warning("⚠️  NewsAPI key not set. Skipping NewsAPI monitoring.")
            return

        logger.info(f"📰 Starting NewsAPI monitor (interval: {interval}s)")

        while True:
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": "forex OR currency OR economy OR central bank OR interest rate",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": max_results,
                    "apiKey": self.newsapi_key
                }

                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])

                    new_count = 0
                    for article in articles:
                        headline = article.get('title', '')
                        if headline and headline not in self.seen_headlines:
                            self.seen_headlines.add(headline)
                            await self.news_queue.put({
                                "headline": headline,
                                "source": "NewsAPI",
                                "timestamp": datetime.now().isoformat()
                            })
                            new_count += 1

                    if new_count > 0:
                        logger.info(f"✅ NewsAPI: {new_count} new headlines queued")
                else:
                    logger.error(f"❌ NewsAPI error: {response.status_code}")

            except Exception as e:
                logger.error(f"❌ NewsAPI monitor error: {e}")
                self.stats["errors"] += 1

            await asyncio.sleep(interval)

    async def monitor_rss_feed(self, name: str, feed_url: str, interval: int = 60):
        """Monitor RSS feed and add new headlines to queue"""
        logger.info(f"📡 Starting RSS monitor: {name} (interval: {interval}s)")

        while True:
            try:
                feed = feedparser.parse(feed_url)

                new_count = 0
                for entry in feed.entries[:20]:
                    headline = entry.get('title', '')
                    if headline and headline not in self.seen_headlines:
                        self.seen_headlines.add(headline)
                        await self.news_queue.put({
                            "headline": headline,
                            "source": name,
                            "timestamp": datetime.now().isoformat()
                        })
                        new_count += 1

                if new_count > 0:
                    logger.info(f"✅ {name}: {new_count} new headlines queued")

            except Exception as e:
                logger.error(f"❌ RSS monitor error ({name}): {e}")
                self.stats["errors"] += 1

            await asyncio.sleep(interval)

    async def process_news_queue(self):
        """Process headlines from queue and broadcast to UI"""
        logger.info("🔄 Starting news queue processor...")

        while True:
            try:
                # Get headline from queue
                news_item = await self.news_queue.get()
                headline = news_item["headline"]
                source = news_item["source"]

                self.stats["total_headlines"] += 1

                logger.info(f"\n{'='*80}")
                logger.info(f"📰 [{source}] {headline}")

                # Analyze headline AND broadcast to all connected clients
                try:
                    response = requests.post(
                        f"{self.analyzer_url}/broadcast",
                        json={
                            "headline": headline,
                            "min_confidence": 0.3,
                            "llm_provider": "mock"
                        },
                        timeout=15
                    )

                    if response.status_code == 200:
                        result = response.json()
                        analysis_result = result.get('result', {})
                        entities = analysis_result.get('impacted_entities', [])
                        clients_notified = result.get('clients_notified', 0)

                        self.stats["analyzed"] += 1

                        logger.info(f"⏱️  Processing time: {analysis_result.get('processing_time_ms', 0):.0f}ms")
                        logger.info(f"💱 Impacted currencies: {len(entities)}")
                        logger.info(f"📡 Broadcast to {clients_notified} connected clients")

                        # Show top impacts
                        for i, entity in enumerate(entities[:3], 1):
                            emoji = "🟢" if entity['confidence'] == "high" else "🟡" if entity['confidence'] == "medium" else "🔴"
                            logger.info(
                                f"   {emoji} #{i} {entity['currency']}: "
                                f"{entity['confidence'].upper()} ({entity['confidence_score']:.2f})"
                            )

                    else:
                        logger.error(f"❌ Analyzer error: {response.status_code}")
                        self.stats["errors"] += 1

                except requests.exceptions.Timeout:
                    logger.error("⏱️  Analyzer timeout")
                    self.stats["errors"] += 1
                except Exception as e:
                    logger.error(f"❌ Processing error: {e}")
                    self.stats["errors"] += 1

                # Mark task as done
                self.news_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Queue processor error: {e}")


    async def stats_reporter(self, interval: int = 300):
        """Report statistics periodically"""
        logger.info(f"📊 Starting stats reporter (interval: {interval}s)")

        while True:
            await asyncio.sleep(interval)

            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            rate = self.stats['analyzed'] / (uptime / 60) if uptime > 0 else 0

            logger.info(f"\n{'='*80}")
            logger.info("📊 TICKER STATISTICS")
            logger.info(f"{'='*80}")
            logger.info(f"⏱️  Uptime: {uptime/60:.1f} minutes")
            logger.info(f"📰 Total headlines seen: {self.stats['total_headlines']}")
            logger.info(f"✅ Successfully analyzed: {self.stats['analyzed']}")
            logger.info(f"❌ Errors: {self.stats['errors']}")
            logger.info(f"📈 Analysis rate: {rate:.2f} headlines/minute")
            logger.info(f"💾 Unique headlines tracked: {len(self.seen_headlines)}")
            logger.info(f"⏳ Queue size: {self.news_queue.qsize()}")
            logger.info(f"{'='*80}\n")

    async def start(self):
        """Start all monitoring tasks"""
        logger.info("=" * 80)
        logger.info("🚀 BLOOMBERG-STYLE NEWS TICKER STARTING")
        logger.info("=" * 80)
        logger.info(f"🎯 Analyzer URL: {self.analyzer_url}")
        logger.info(f"🔑 NewsAPI key: {'✅ Set' if self.newsapi_key else '❌ Not set'}")
        logger.info(f"📡 RSS feeds: {len(self.rss_feeds)}")
        logger.info("=" * 80)

        # Check if analyzer is running
        try:
            response = requests.get(f"{self.analyzer_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Analyzer service is running")
            else:
                logger.error("❌ Analyzer service not healthy")
                return
        except:
            logger.error("❌ Cannot connect to analyzer. Please start the API service first:")
            logger.error("   python3 api_service.py")
            return

        # Create monitoring tasks
        tasks = []

        # NewsAPI monitor (if key available)
        if self.newsapi_key:
            tasks.append(self.monitor_newsapi(interval=300, max_results=20))

        # RSS feed monitors
        for name, url in self.rss_feeds:
            tasks.append(self.monitor_rss_feed(name, url, interval=60))

        # Queue processor (processes and broadcasts to UI)
        tasks.append(self.process_news_queue())

        # Stats reporter
        tasks.append(self.stats_reporter(interval=300))

        logger.info(f"\n✅ Started {len(tasks)} tasks")
        logger.info("📺 News ticker is live - results will be broadcast to UI")
        logger.info("🔄 Press Ctrl+C to stop\n")

        # Run all tasks
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down...")
            logger.info("📊 Final Statistics:")
            logger.info(f"   Total headlines: {self.stats['total_headlines']}")
            logger.info(f"   Analyzed: {self.stats['analyzed']}")
            logger.info(f"   Errors: {self.stats['errors']}")
            logger.info("✅ Ticker stopped")


async def main():
    """Main entry point"""
    ticker = NewsTickerService()
    await ticker.start()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   📺 Bloomberg-Style News Ticker Service                 ║
║   Real-time news monitoring with auto-broadcast to UI     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Prerequisites:
  1. Start the API service first:
     python3 api_service.py

  2. (Optional) Set NewsAPI key for more news sources:
     export NEWSAPI_KEY="your-api-key"

  3. Open UI in browser:
     http://localhost:8501

Starting ticker service...
""")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Ticker stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
