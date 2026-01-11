# Real-Time News Sources Guide

## 🎯 Quick Start

### Option 1: Use the Simulator (Easiest)

```bash
python3 news_feed_simulator.py
```

Choose from:
1. Generate fake headlines (for testing)
2. Stream to WebSocket (real-time simulation)
3. Stream to API (REST simulation)
4. Fetch real news from NewsAPI
5. Fetch real news from RSS

### Option 2: Real News APIs (Recommended)

## 📰 Free News APIs

### 1. NewsAPI.org (Best for Testing)

**Setup:**
```bash
# Get free API key: https://newsapi.org/
export NEWSAPI_KEY="your-api-key"
```

**Usage:**
```python
import requests

api_key = "your-api-key"
url = f"https://newsapi.org/v2/everything?q=forex OR economy&apiKey={api_key}"
response = requests.get(url)
articles = response.json()['articles']

for article in articles:
    headline = article['title']
    # Send to your analyzer
```

**Free Tier:**
- 100 requests/day
- 80,000+ sources
- Real-time updates

**Categories:**
- `business`, `finance`, `general`
- Query: `"forex OR currency OR central bank"`

---

### 2. Alpha Vantage (Financial Focus)

**Setup:**
```bash
# Get free API key: https://www.alphavantage.co/
export ALPHAVANTAGE_KEY="your-api-key"
```

**Usage:**
```python
url = f"https://www.alphavantage.co/query"
params = {
    "function": "NEWS_SENTIMENT",
    "apikey": api_key,
    "topics": "finance"
}
response = requests.get(url, params=params)
```

**Free Tier:**
- 25 requests/day
- Financial news focus
- Sentiment scores included

---

### 3. Finnhub (Real-Time Financial)

**Setup:**
```bash
# Get free API key: https://finnhub.io/
export FINNHUB_KEY="your-api-key"
```

**Usage:**
```python
url = f"https://finnhub.io/api/v1/news?category=forex&token={api_key}"
response = requests.get(url)
```

**Free Tier:**
- 60 calls/minute
- Real-time market news
- Forex-specific news

---

## 📡 RSS Feeds (No API Key Needed!)

### Free Financial News RSS Feeds

```python
# Reuters Business
"http://feeds.reuters.com/reuters/businessNews"

# Bloomberg Markets
"https://www.bloomberg.com/politics/feeds/site.xml"

# Yahoo Finance
"https://finance.yahoo.com/news/rssindex"

# FT Markets
"https://www.ft.com/markets?format=rss"

# CNBC
"https://www.cnbc.com/id/100003114/device/rss/rss.html"
```

**Usage:**
```bash
# Install feedparser
pip install feedparser

# Use it
python3 news_feed_simulator.py
# Choose option 5
```

---

## 🔥 Live Integration Examples

### Example 1: Stream Real News to Your Analyzer

Create `live_news_streamer.py`:

```python
import asyncio
import requests
import json
import time

async def stream_real_news():
    # Fetch from NewsAPI
    api_key = "your-api-key"
    news_url = f"https://newsapi.org/v2/everything"

    params = {
        "q": "forex OR currency OR central bank",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": api_key
    }

    response = requests.get(news_url, params=params)
    articles = response.json().get('articles', [])

    # Send each headline to your analyzer
    analyzer_url = "http://localhost:8000/analyze"

    for article in articles:
        headline = article['title']

        print(f"📰 {headline}")

        # Analyze
        result = requests.post(analyzer_url, json={
            "headline": headline,
            "min_confidence": 0.3,
            "llm_provider": "mock"
        })

        if result.status_code == 200:
            data = result.json()
            entities = data.get('impacted_entities', [])

            if entities:
                top = entities[0]
                print(f"   💱 {top['currency']}: {top['confidence'].upper()}")

        await asyncio.sleep(2)  # Rate limiting

asyncio.run(stream_real_news())
```

---

### Example 2: WebSocket Real News Stream

```python
import websocket
import json
import requests

# Fetch news
api_key = "your-newsapi-key"
url = f"https://newsapi.org/v2/everything?q=forex&apiKey={api_key}"
articles = requests.get(url).json()['articles']

# Connect to WebSocket
ws = websocket.create_connection("ws://localhost:8000/ws/stream")

# Stream headlines
for article in articles[:5]:
    headline = article['title']

    ws.send(json.dumps({
        "headline": headline,
        "llm_provider": "mock"
    }))

    result = json.loads(ws.recv())
    print(f"✅ {headline[:50]}... → {len(result['data']['impacted_entities'])} currencies impacted")

ws.close()
```

---

### Example 3: RSS Feed Monitor

```python
import feedparser
import time
import requests

feed_url = "http://feeds.reuters.com/reuters/businessNews"
analyzer_url = "http://localhost:8000/analyze"

seen_headlines = set()

while True:
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        headline = entry.title

        if headline not in seen_headlines:
            seen_headlines.add(headline)

            print(f"\n📰 NEW: {headline}")

            # Analyze
            response = requests.post(analyzer_url, json={
                "headline": headline,
                "llm_provider": "mock"
            })

            if response.status_code == 200:
                result = response.json()
                entities = result.get('impacted_entities', [])

                for entity in entities[:3]:
                    print(f"   💱 {entity['currency']}: {entity['confidence'].upper()} ({entity['confidence_score']:.2f})")

    print(f"\n⏳ Checking for new headlines in 60s...")
    time.sleep(60)  # Check every minute
```

---

## 🚀 Production-Ready Integration

### Complete News Feed Service

Create `news_feed_service.py`:

```python
"""
Production News Feed Service
Continuously monitors news sources and streams to analyzer
"""

import asyncio
import requests
import feedparser
from datetime import datetime
import json
import websocket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsFeedService:
    def __init__(self, newsapi_key=None):
        self.newsapi_key = newsapi_key
        self.analyzer_url = "http://localhost:8000/analyze"
        self.ws_url = "ws://localhost:8000/ws/stream"
        self.seen_headlines = set()

    async def monitor_newsapi(self, interval=300):
        """Monitor NewsAPI every 5 minutes"""
        while True:
            try:
                url = f"https://newsapi.org/v2/everything"
                params = {
                    "q": "forex OR currency OR central bank",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                    "apiKey": self.newsapi_key
                }

                response = requests.get(url, params=params)
                articles = response.json().get('articles', [])

                new_count = 0
                for article in articles:
                    headline = article['title']
                    if headline not in self.seen_headlines:
                        self.seen_headlines.add(headline)
                        await self.process_headline(headline)
                        new_count += 1

                logger.info(f"✅ Checked NewsAPI: {new_count} new headlines")

            except Exception as e:
                logger.error(f"❌ NewsAPI error: {e}")

            await asyncio.sleep(interval)

    async def monitor_rss(self, feed_url, interval=60):
        """Monitor RSS feed every minute"""
        while True:
            try:
                feed = feedparser.parse(feed_url)

                new_count = 0
                for entry in feed.entries:
                    headline = entry.title
                    if headline not in self.seen_headlines:
                        self.seen_headlines.add(headline)
                        await self.process_headline(headline)
                        new_count += 1

                logger.info(f"✅ Checked RSS: {new_count} new headlines")

            except Exception as e:
                logger.error(f"❌ RSS error: {e}")

            await asyncio.sleep(interval)

    async def process_headline(self, headline):
        """Process a single headline"""
        logger.info(f"📰 {headline}")

        try:
            response = requests.post(self.analyzer_url, json={
                "headline": headline,
                "llm_provider": "mock"
            }, timeout=10)

            if response.status_code == 200:
                result = response.json()
                entities = result.get('impacted_entities', [])

                if entities:
                    top = entities[0]
                    logger.info(f"   💱 Top: {top['currency']} ({top['confidence'].upper()})")

        except Exception as e:
            logger.error(f"❌ Processing error: {e}")

    async def start(self):
        """Start all monitors"""
        tasks = []

        if self.newsapi_key:
            tasks.append(self.monitor_newsapi(interval=300))

        # Monitor multiple RSS feeds
        rss_feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://finance.yahoo.com/news/rssindex"
        ]

        for feed_url in rss_feeds:
            tasks.append(self.monitor_rss(feed_url, interval=60))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    import os

    api_key = os.getenv("NEWSAPI_KEY")
    service = NewsFeedService(newsapi_key=api_key)

    logger.info("🚀 Starting News Feed Service...")
    asyncio.run(service.start())
```

**Run it:**
```bash
export NEWSAPI_KEY="your-key"
python3 news_feed_service.py
```

---

## 📊 Comparison of News Sources

| Source | Free Tier | Rate Limit | Real-Time | API Key | Best For |
|--------|-----------|------------|-----------|---------|----------|
| NewsAPI | ✅ 100/day | Good | 15 min delay | Required | General testing |
| Finnhub | ✅ 60/min | Excellent | Real-time | Required | Financial news |
| Alpha Vantage | ✅ 25/day | Limited | Real-time | Required | Analysis |
| Reuters RSS | ✅ Unlimited | Good | Real-time | No | Production |
| Yahoo RSS | ✅ Unlimited | Good | Real-time | No | Production |

---

## 🎯 Recommended Setup

### For Testing:
```bash
# Use the simulator
python3 news_feed_simulator.py
```

### For Development:
```bash
# Use RSS feeds (no API key)
python3 news_feed_simulator.py  # Choose option 5
```

### For Production:
```bash
# Get NewsAPI key + use RSS feeds
export NEWSAPI_KEY="your-key"
python3 news_feed_service.py
```

---

## 💡 Pro Tips

1. **Start with RSS** - No API key needed, works immediately
2. **Add NewsAPI** - For more variety, 100/day is enough
3. **Use Finnhub** - Best for real-time financial news
4. **Combine Sources** - Monitor multiple feeds
5. **Rate Limiting** - Respect API limits
6. **Deduplication** - Track seen headlines
7. **Error Handling** - APIs can fail, have fallbacks

---

## 🔧 Quick Commands

```bash
# Test with simulator
python3 news_feed_simulator.py

# Get real news (RSS)
python3 -c "
import feedparser
feed = feedparser.parse('http://feeds.reuters.com/reuters/businessNews')
for entry in feed.entries[:5]:
    print(entry.title)
"

# Install dependencies
pip install feedparser requests websocket-client

# Start monitoring service
export NEWSAPI_KEY='your-key'
python3 news_feed_service.py
```

---

**Next Steps:**
1. Try the simulator first
2. Get a NewsAPI key (free)
3. Test with RSS feeds
4. Build your production service

Ready to stream real news! 📰🚀
