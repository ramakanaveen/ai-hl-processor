"""
Production News Feed Service
Continuously monitors news sources and streams analysis results
Run: python3 news_feed_service.py
"""

import asyncio
import requests
import feedparser
from datetime import datetime
import json
import logging
import os
from typing import Set, List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsFeedService:
    """Production-ready news feed monitoring service"""

    def __init__(self, newsapi_key: str = None, analyzer_url: str = "http://localhost:8000/analyze"):
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        self.analyzer_url = analyzer_url
        self.seen_headlines: Set[str] = set()
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
        """
        Monitor NewsAPI for new headlines
        interval: seconds between checks (default: 5 minutes)
        """
        if not self.newsapi_key:
            logger.warning("⚠️  NewsAPI key not set. Skipping NewsAPI monitoring.")
            logger.info("💡 Get a free key from https://newsapi.org/")
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
                            await self.process_headline(headline, source="NewsAPI")
                            new_count += 1

                    logger.info(f"✅ NewsAPI: {new_count} new headlines ({len(articles)} total)")
                else:
                    logger.error(f"❌ NewsAPI error: {response.status_code}")

            except Exception as e:
                logger.error(f"❌ NewsAPI monitor error: {e}")
                self.stats["errors"] += 1

            await asyncio.sleep(interval)

    async def monitor_rss_feed(self, name: str, feed_url: str, interval: int = 60):
        """
        Monitor a single RSS feed
        interval: seconds between checks (default: 1 minute)
        """
        logger.info(f"📡 Starting RSS monitor: {name} (interval: {interval}s)")

        while True:
            try:
                feed = feedparser.parse(feed_url)

                new_count = 0
                for entry in feed.entries[:20]:  # Limit to 20 most recent
                    headline = entry.get('title', '')
                    if headline and headline not in self.seen_headlines:
                        self.seen_headlines.add(headline)
                        await self.process_headline(headline, source=name)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"✅ {name}: {new_count} new headlines")

            except Exception as e:
                logger.error(f"❌ RSS monitor error ({name}): {e}")
                self.stats["errors"] += 1

            await asyncio.sleep(interval)

    async def process_headline(self, headline: str, source: str = "Unknown"):
        """Process a single headline through the analyzer"""
        self.stats["total_headlines"] += 1

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"📰 [{source}] {headline}")

            # Analyze headline
            response = requests.post(
                self.analyzer_url,
                json={
                    "headline": headline,
                    "min_confidence": 0.3,
                    "llm_provider": "mock"  # Change to "gemini_flash" for production
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                entities = result.get('impacted_entities', [])

                self.stats["analyzed"] += 1

                logger.info(f"⏱️  Processing time: {result.get('processing_time_ms', 0):.0f}ms")
                logger.info(f"💱 Impacted currencies: {len(entities)}")

                # Show top 3 impacts
                for i, entity in enumerate(entities[:3], 1):
                    emoji = "🟢" if entity['confidence'] == "high" else "🟡" if entity['confidence'] == "medium" else "🔴"
                    logger.info(
                        f"   {emoji} #{i} {entity['currency']}: "
                        f"{entity['confidence'].upper()} ({entity['confidence_score']:.2f}) - "
                        f"{entity['reasoning'][:60]}..."
                    )

                if len(entities) == 0:
                    logger.info("   ℹ️  No significant currency impacts detected")

            else:
                logger.error(f"❌ Analyzer error: {response.status_code}")
                self.stats["errors"] += 1

        except requests.exceptions.Timeout:
            logger.error("⏱️  Analyzer timeout")
            self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            self.stats["errors"] += 1

    async def stats_reporter(self, interval: int = 300):
        """Report statistics periodically"""
        logger.info(f"📊 Starting stats reporter (interval: {interval}s)")

        while True:
            await asyncio.sleep(interval)

            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            rate = self.stats['analyzed'] / (uptime / 60) if uptime > 0 else 0

            logger.info(f"\n{'='*80}")
            logger.info("📊 STATISTICS REPORT")
            logger.info(f"{'='*80}")
            logger.info(f"⏱️  Uptime: {uptime/60:.1f} minutes")
            logger.info(f"📰 Total headlines seen: {self.stats['total_headlines']}")
            logger.info(f"✅ Successfully analyzed: {self.stats['analyzed']}")
            logger.info(f"❌ Errors: {self.stats['errors']}")
            logger.info(f"📈 Analysis rate: {rate:.2f} headlines/minute")
            logger.info(f"💾 Unique headlines tracked: {len(self.seen_headlines)}")
            logger.info(f"{'='*80}\n")

    async def start(self):
        """Start all monitoring tasks"""
        logger.info("=" * 80)
        logger.info("🚀 NEWS FEED SERVICE STARTING")
        logger.info("=" * 80)
        logger.info(f"🎯 Analyzer URL: {self.analyzer_url}")
        logger.info(f"🔑 NewsAPI key: {'✅ Set' if self.newsapi_key else '❌ Not set'}")
        logger.info(f"📡 RSS feeds: {len(self.rss_feeds)}")
        logger.info("=" * 80)

        # Check if analyzer is running
        try:
            response = requests.get(self.analyzer_url.replace('/analyze', '/health'), timeout=5)
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

        # NewsAPI monitor
        if self.newsapi_key:
            tasks.append(self.monitor_newsapi(interval=300, max_results=20))

        # RSS feed monitors
        for name, url in self.rss_feeds:
            tasks.append(self.monitor_rss_feed(name, url, interval=60))

        # Stats reporter
        tasks.append(self.stats_reporter(interval=300))

        logger.info(f"\n✅ Started {len(tasks)} monitoring tasks")
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
            logger.info("✅ Service stopped")


async def main():
    """Main entry point"""
    service = NewsFeedService()
    await service.start()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   📰 AI Headline Impact Analyzer - News Feed Service     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Prerequisites:
  1. Start the API service first:
     python3 api_service.py

  2. (Optional) Set NewsAPI key for more news sources:
     export NEWSAPI_KEY="your-api-key"
     Get one free from: https://newsapi.org/

Starting service...
""")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Service stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
