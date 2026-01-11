"""
News Feed Simulator for Testing
Simulates real-time news headlines for testing the streaming feature
"""

import asyncio
import random
import time
from datetime import datetime
from typing import List
import requests
import json


class NewsFeedSimulator:
    """Simulates a real-time news feed"""

    def __init__(self):
        self.sample_headlines = [
            "Federal Reserve raises interest rates by 0.75 basis points amid inflation concerns",
            "ECB President signals potential emergency bond buying program",
            "Bank of England emergency intervention in UK gilt market",
            "Russia launches missile attack on Ukrainian energy infrastructure",
            "OPEC+ announces surprise oil production cut of 2 million barrels per day",
            "China announces new trade restrictions on semiconductor exports",
            "Japan intervenes in currency markets as yen hits 32-year low",
            "Switzerland central bank intervenes to support franc",
            "Rachel Reeves announces major tax increase in UK budget",
            "European Union unveils new sanctions package against Russia",
            "US jobs report shows unexpected surge in unemployment",
            "Germany reports surprise GDP contraction",
            "Oil prices surge 10% on Middle East tensions",
            "Gold hits new record high on safe haven demand",
            "Tech stocks plunge on regulatory concerns",
            "Bitcoin crashes 15% on exchange collapse fears",
            "IMF downgrades global growth forecast",
            "World Bank warns of impending recession",
            "Turkey central bank cuts rates despite high inflation",
            "Brazil raises interest rates to 15-year high"
        ]

    async def generate_headlines(self, interval: float = 3.0, count: int = 10):
        """Generate headlines at regular intervals"""
        print(f"📰 Starting news feed simulation (interval: {interval}s, count: {count})")
        print("=" * 80)

        for i in range(count):
            headline = random.choice(self.sample_headlines)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n[{timestamp}] News #{i+1}:")
            print(f"  📌 {headline}")

            yield {
                "headline": headline,
                "timestamp": timestamp,
                "source": "Simulated Feed"
            }

            await asyncio.sleep(interval)

    async def stream_to_websocket(self, websocket_url: str = "ws://localhost:8000/ws/stream",
                                 interval: float = 3.0, count: int = 10):
        """Stream headlines to WebSocket endpoint"""
        try:
            import websocket as ws

            print(f"🔌 Connecting to WebSocket: {websocket_url}")
            socket = ws.create_connection(websocket_url)
            print("✅ Connected!")

            async for news_item in self.generate_headlines(interval, count):
                # Send to WebSocket
                message = {
                    "headline": news_item["headline"],
                    "min_confidence": 0.3,
                    "llm_provider": "mock"
                }

                print(f"  📤 Sending to WebSocket...")
                socket.send(json.dumps(message))

                # Receive response
                response = socket.recv()
                data = json.loads(response)

                if data.get('status') == 'completed':
                    result = data['data']
                    entities = result.get('impacted_entities', [])
                    print(f"  ✅ Analysis complete!")
                    print(f"  💱 Impacted currencies: {len(entities)}")

                    if entities:
                        top_entity = entities[0]
                        print(f"     Top impact: {top_entity['currency']} "
                              f"({top_entity['confidence'].upper()}, {top_entity['confidence_score']:.2f})")

            socket.close()
            print("\n" + "=" * 80)
            print("✅ Simulation complete!")

        except Exception as e:
            print(f"❌ Error: {e}")

    async def stream_to_api(self, api_url: str = "http://localhost:8000/analyze",
                          interval: float = 3.0, count: int = 10):
        """Stream headlines to REST API endpoint"""
        print(f"🔌 Streaming to API: {api_url}")

        async for news_item in self.generate_headlines(interval, count):
            # Send to API
            payload = {
                "headline": news_item["headline"],
                "min_confidence": 0.3,
                "llm_provider": "mock"
            }

            print(f"  📤 Sending to API...")
            response = requests.post(api_url, json=payload)

            if response.status_code == 200:
                result = response.json()
                entities = result.get('impacted_entities', [])
                print(f"  ✅ Analysis complete!")
                print(f"  💱 Impacted currencies: {len(entities)}")

                if entities:
                    top_entity = entities[0]
                    print(f"     Top impact: {top_entity['currency']} "
                          f"({top_entity['confidence'].upper()}, {top_entity['confidence_score']:.2f})")
            else:
                print(f"  ❌ API error: {response.status_code}")

        print("\n" + "=" * 80)
        print("✅ Simulation complete!")


class RealNewsFeed:
    """Fetch real news from various sources"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    async def fetch_newsapi(self, query: str = "finance OR economy OR forex",
                          max_results: int = 10):
        """Fetch from NewsAPI.org"""
        if not self.api_key:
            print("❌ API key required. Get one from https://newsapi.org/")
            return

        url = f"https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "apiKey": self.api_key
        }

        print(f"📰 Fetching news from NewsAPI.org...")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])

            print(f"✅ Found {len(articles)} articles")
            print("=" * 80)

            for i, article in enumerate(articles, 1):
                headline = article.get('title', '')
                source = article.get('source', {}).get('name', 'Unknown')
                published = article.get('publishedAt', '')

                print(f"\n[{i}] {source} - {published}")
                print(f"    {headline}")

                yield {
                    "headline": headline,
                    "source": source,
                    "timestamp": published,
                    "url": article.get('url')
                }
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())

    async def fetch_rss_feed(self, feed_url: str = "http://feeds.reuters.com/reuters/businessNews"):
        """Fetch from RSS feed"""
        try:
            import feedparser

            print(f"📰 Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            print(f"✅ Found {len(feed.entries)} entries")
            print("=" * 80)

            for i, entry in enumerate(feed.entries[:10], 1):
                headline = entry.get('title', '')
                published = entry.get('published', '')

                print(f"\n[{i}] {published}")
                print(f"    {headline}")

                yield {
                    "headline": headline,
                    "source": "RSS Feed",
                    "timestamp": published,
                    "url": entry.get('link')
                }

        except ImportError:
            print("❌ feedparser not installed. Run: pip install feedparser")
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main demonstration"""
    import sys

    print("=" * 80)
    print("📰 News Feed Simulator for AI Headline Impact Analyzer")
    print("=" * 80)

    print("\nChoose mode:")
    print("1. Simulate news feed (fake headlines)")
    print("2. WebSocket streaming (simulated)")
    print("3. API streaming (simulated)")
    print("4. Fetch real news from NewsAPI.org")
    print("5. Fetch real news from RSS feed")

    choice = input("\nEnter choice (1-5): ").strip()

    simulator = NewsFeedSimulator()

    if choice == "1":
        # Just generate headlines
        async for news in simulator.generate_headlines(interval=2.0, count=5):
            pass

    elif choice == "2":
        # Stream to WebSocket
        print("\n⚠️  Make sure API service is running: python3 api_service.py")
        input("Press Enter to continue...")
        await simulator.stream_to_websocket(interval=2.0, count=5)

    elif choice == "3":
        # Stream to REST API
        print("\n⚠️  Make sure API service is running: python3 api_service.py")
        input("Press Enter to continue...")
        await simulator.stream_to_api(interval=2.0, count=5)

    elif choice == "4":
        # Fetch real news from NewsAPI
        api_key = input("\nEnter NewsAPI.org API key (or press Enter to skip): ").strip()
        if api_key:
            real_feed = RealNewsFeed(api_key)
            async for news in real_feed.fetch_newsapi():
                pass
        else:
            print("❌ API key required. Get one from https://newsapi.org/")

    elif choice == "5":
        # Fetch from RSS
        print("\n📰 Default: Reuters Business News")
        custom_url = input("Enter RSS URL (or press Enter for default): ").strip()
        feed_url = custom_url if custom_url else "http://feeds.reuters.com/reuters/businessNews"

        real_feed = RealNewsFeed()
        async for news in real_feed.fetch_rss_feed(feed_url):
            pass

    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
