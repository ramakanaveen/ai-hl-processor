# Complete Setup Guide - Real-Time News Analysis System

## 🎯 What You Have Now

A complete real-time news analysis system with:
- ✅ **Multi-LLM Support** (Mock, Gemini Flash, Claude)
- ✅ **WebSocket Streaming** (Real-time analysis)
- ✅ **Dual-Mode UI** (Request/Response + Live Stream)
- ✅ **Real News Integration** (NewsAPI, RSS feeds)
- ✅ **Production-Ready Service** (Continuous monitoring)

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start the API + UI

```bash
python3 start_services.py
```

This starts:
- FastAPI backend: http://localhost:8000
- Streamlit UI: http://localhost:8501

### Step 2: Test with Simulator

```bash
# In a new terminal
python3 news_feed_simulator.py
```

Choose option 2 or 3 to stream test headlines.

### Step 3: Open the UI

Open http://localhost:8501 and:
1. Select LLM provider (Mock for testing)
2. Try "Request/Response" tab for single headlines
3. Try "Live Stream" tab for real-time monitoring

**That's it!** 🎉 You're analyzing news in real-time.

---

## 📁 Files Overview

### Core System (Phase 1)
- `main.py` - CLI interface (still works)
- `poc_implementation.py` - Analysis engine
- `semantic_impact_engine.py` - Event extraction
- `economic_knowledge_graph.py` - Economic relationships
- `feature_engineering.py` - Feature extraction
- `config_loader.py` - Configuration management

### API Layer (Phase 1)
- `models.py` - Pydantic data models
- `api_service.py` - FastAPI backend with WebSocket

### LLM Integration (Phase 1.5)
- `llm_providers.py` - Multi-provider abstraction
  - MockLLMClient
  - GeminiFlashClient
  - ClaudeClient
  - LLMClientFactory

### User Interface (Phase 1.5)
- `streamlit_app.py` - Dual-mode UI
  - Tab 1: Request/Response
  - Tab 2: Live Stream
  - LLM provider selector

### News Integration (New!)
- `news_feed_simulator.py` - Test with fake headlines
- `news_feed_service.py` - Production news monitoring
- `REAL_NEWS_SOURCES.md` - Complete guide

### Documentation
- `README.md` - Main project docs
- `CLAUDE.md` - Architecture guide
- `PHASE1_README.md` - Phase 1 guide
- `PHASE1.5_FEATURES.md` - New features guide
- `REAL_NEWS_SOURCES.md` - News sources guide
- `COMPLETE_SETUP_GUIDE.md` - This file

### Scripts
- `start_services.py` - One-command startup
- `test_integration.py` - Integration tests

---

## 🎮 Usage Modes

### Mode 1: Interactive UI (Easiest)

```bash
python3 start_services.py
# Open http://localhost:8501
```

**Use Cases:**
- Test single headlines
- Monitor live news stream
- Switch LLM providers
- Export results

### Mode 2: Test with Simulator

```bash
# Terminal 1: Start services
python3 start_services.py

# Terminal 2: Run simulator
python3 news_feed_simulator.py
```

**Simulator Options:**
1. Generate fake headlines
2. Stream to WebSocket
3. Stream to API
4. Fetch from NewsAPI
5. Fetch from RSS

### Mode 3: Production Monitoring

```bash
# Terminal 1: Start services
python3 start_services.py

# Terminal 2: Start news monitoring
export NEWSAPI_KEY="your-key"  # Optional
python3 news_feed_service.py
```

**What it does:**
- Monitors NewsAPI (if key provided)
- Monitors 3 RSS feeds (Reuters, Yahoo, Bloomberg)
- Analyzes every new headline
- Shows top currency impacts
- Reports statistics every 5 minutes

### Mode 4: API Integration

```bash
# REST API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Fed raises interest rates",
    "llm_provider": "mock"
  }'

# WebSocket
python3 -c "
import websocket
import json

ws = websocket.create_connection('ws://localhost:8000/ws/stream')
ws.send(json.dumps({'headline': 'ECB bond buying'}))
print(json.loads(ws.recv()))
ws.close()
"
```

---

## 🤖 LLM Provider Setup

### Mock LLM (Default - No Setup Required)
```bash
# Already works! Just select "Mock LLM" in UI
```

**Features:**
- Fast (100-200ms)
- No API key needed
- Realistic responses
- Perfect for testing

### Google Gemini Flash (Production)

**1. Setup Google Cloud:**
```bash
# Set project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Set credentials path
export GOOGLE_CREDENTIALS_PATH="/path/to/service-account.json"
```

**2. In UI:**
- Select "Google Gemini Flash" from dropdown

**3. In API:**
```json
{
  "headline": "...",
  "llm_provider": "gemini_flash"
}
```

### Anthropic Claude (Optional)

**1. Install:**
```bash
pip install anthropic
```

**2. Setup API Key:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**3. In UI:**
- Select "Anthropic Claude" from dropdown

---

## 📰 Real News Sources

### Option 1: RSS Feeds (Free, No API Key)

**Already configured in `news_feed_service.py`:**
- Reuters Business News
- Yahoo Finance
- Bloomberg

**Run it:**
```bash
python3 news_feed_service.py
```

### Option 2: NewsAPI.org (Free Tier)

**1. Get API Key:**
- Visit https://newsapi.org/
- Register for free
- Get API key (100 requests/day)

**2. Set Environment:**
```bash
export NEWSAPI_KEY="your-api-key"
```

**3. Run:**
```bash
python3 news_feed_service.py
```

### Option 3: Other Sources

**Finnhub (Financial):**
```bash
export FINNHUB_KEY="your-api-key"
# Modify news_feed_service.py to add Finnhub
```

**Alpha Vantage:**
```bash
export ALPHAVANTAGE_KEY="your-api-key"
# See REAL_NEWS_SOURCES.md for integration
```

---

## 🎯 Common Workflows

### Workflow 1: Quick Test

```bash
# 1. Start services
python3 start_services.py

# 2. Open UI
# http://localhost:8501

# 3. Select "Mock LLM"

# 4. Try example headline
# Click "📈 Fed raises interest rates"

# 5. View results!
```

### Workflow 2: Live News Monitoring

```bash
# 1. Start services
python3 start_services.py

# 2. Start news monitor
python3 news_feed_service.py

# 3. Watch terminal for analysis results

# 4. Open UI to see stream
# http://localhost:8501 → Live Stream tab
```

### Workflow 3: Custom News Feed

```python
# Create custom_news_feed.py
import requests

headlines = [
    "Your custom headline 1",
    "Your custom headline 2",
]

for headline in headlines:
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"headline": headline, "llm_provider": "mock"}
    )
    print(response.json())
```

```bash
python3 custom_news_feed.py
```

### Workflow 4: Production Deployment

```bash
# 1. Set production environment
export ENV=prod
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CREDENTIALS_PATH="/path/to/creds.json"

# 2. Start services
python3 start_services.py

# 3. In UI: Select "Google Gemini Flash"

# 4. Start news monitoring
export NEWSAPI_KEY="your-key"
python3 news_feed_service.py

# 5. Monitor at http://localhost:8501
```

---

## 🧪 Testing

### Test 1: API Health

```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "environment": "test",
  "model_provider": "mock_llm"
}
```

### Test 2: Single Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"headline": "Fed raises rates"}'
```

### Test 3: WebSocket

```bash
python3 -c "
import websocket
import json

ws = websocket.create_connection('ws://localhost:8000/ws/stream')
ws.send(json.dumps({'headline': 'Test'}))
result = json.loads(ws.recv())
print('✅ WebSocket working' if result.get('status') else '❌ Failed')
ws.close()
"
```

### Test 4: News Simulator

```bash
python3 news_feed_simulator.py
# Choose option 2 (WebSocket streaming)
```

### Test 5: RSS Feeds

```bash
python3 -c "
import feedparser
feed = feedparser.parse('http://feeds.reuters.com/reuters/businessNews')
print(f'✅ RSS working: {len(feed.entries)} articles')
print(feed.entries[0].title)
"
```

---

## 📊 Monitoring & Stats

### View API Stats

```bash
curl http://localhost:8000/stats
```

Or in UI: Sidebar → "Get API Stats"

### View News Service Stats

The news_feed_service.py shows:
- Headlines processed
- Analysis rate
- Error count
- Uptime

Reports every 5 minutes automatically.

---

## 🐛 Troubleshooting

### Issue: API won't start

**Error:** `Address already in use`

**Solution:**
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Restart
python3 start_services.py
```

### Issue: WebSocket connection fails

**Error:** `Connection refused`

**Solution:**
1. Ensure API is running: `curl http://localhost:8000/health`
2. Check WebSocket URL: `ws://` not `http://`
3. Check browser console for errors

### Issue: News service no results

**Error:** No headlines appearing

**Solution:**
1. Check API is running
2. Verify RSS feeds are accessible
3. Check logs for errors
4. Try with NewsAPI key for more sources

### Issue: LLM provider errors

**Error:** `Error calling Gemini Flash`

**Solution:**
```bash
# Check credentials
echo $GOOGLE_CLOUD_PROJECT
echo $GOOGLE_CREDENTIALS_PATH

# Verify file exists
ls $GOOGLE_CREDENTIALS_PATH

# Test with Mock provider first
# Select "Mock LLM" in UI
```

---

## 📈 Performance

| Component | Performance |
|-----------|-------------|
| Mock LLM | 100-200ms |
| Gemini Flash | 500-1500ms |
| Claude | 800-2000ms |
| WebSocket | <100ms overhead |
| RSS Fetch | 200-500ms |
| NewsAPI Fetch | 300-800ms |

**Optimization Tips:**
1. Use Mock LLM for high volume
2. Batch process with API
3. Cache results
4. Use concurrent processing

---

## 🔮 Next Steps

### Immediate:
- [x] Test with simulator
- [ ] Get NewsAPI key
- [ ] Try RSS feeds
- [ ] Test all LLM providers

### Short-term:
- [ ] Connect to real news feed
- [ ] Monitor for 24 hours
- [ ] Analyze results
- [ ] Export to database

### Long-term:
- [ ] Add more LLM providers (OpenAI, Cohere)
- [ ] Implement caching (Redis)
- [ ] Add authentication
- [ ] Deploy to Kubernetes
- [ ] Build historical analysis
- [ ] Create alerts/notifications

---

## 📚 Additional Resources

- **API Docs:** http://localhost:8000/docs (when running)
- **PHASE1.5_FEATURES.md:** New features guide
- **REAL_NEWS_SOURCES.md:** News integration guide
- **CLAUDE.md:** Architecture documentation

---

## 🎓 Example Scripts

All ready to run:
```bash
# Test everything
python3 test_integration.py

# Simulate news
python3 news_feed_simulator.py

# Monitor real news
python3 news_feed_service.py

# Start UI + API
python3 start_services.py
```

---

## ✅ Checklist

Before going to production:

- [ ] Tested with Mock LLM
- [ ] Configured Gemini Flash credentials
- [ ] Got NewsAPI key
- [ ] Tested RSS feeds
- [ ] Verified WebSocket works
- [ ] Tested Live Stream UI
- [ ] Ran news_feed_service.py for 1 hour
- [ ] Checked error rates
- [ ] Set up monitoring
- [ ] Configured rate limiting
- [ ] Tested failover scenarios

---

**You're all set! 🚀**

Start with: `python3 start_services.py`

Then: Open http://localhost:8501

Happy analyzing! 📰💱
