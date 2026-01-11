# Quick Start Guide

Get the AI Headline Impact Processor running in under 2 minutes!

---

## Prerequisites

All dependencies are already installed:
- ✅ Python 3.13
- ✅ FastAPI, Uvicorn, Streamlit
- ✅ All required packages

---

## 3 Simple Steps

### Step 1: Start the Services (One Command!)

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
python3 start_services.py
```

This starts:
- 🚀 FastAPI backend at http://localhost:8000
- 🎨 Streamlit UI at http://localhost:8501

### Step 2: Open the UI

Open your browser to: **http://localhost:8501**

You'll see two tabs:
- **📊 Request / Response** - Test single headlines
- **📡 Live Stream** - Real-time news monitoring

### Step 3: Try It Out!

#### Option A: Test Single Headlines (Request/Response Tab)

1. Select **"Mock LLM (Testing)"** from dropdown (already selected)
2. Click one of the example headlines:
   - 📈 Fed raises interest rates
   - 🏦 ECB bond buying
   - 💷 Bank of England intervention
3. View the results instantly!

#### Option B: Live Stream Testing (Live Stream Tab)

1. Switch to **"Live Stream"** tab
2. Enter a headline like: "Federal Reserve announces rate hike"
3. Click **"Send to Stream"**
4. See the analysis appear in real-time
5. Each new headline gets added to the stream history

---

## Test with Real News (Optional)

### Using the Simulator

In a new terminal:

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
python3 news_feed_simulator.py
```

Choose an option:
- **Option 1**: Generate fake headlines (good for testing)
- **Option 2**: Stream to WebSocket (shows in Live Stream tab)
- **Option 3**: Stream to API (background processing)
- **Option 5**: Fetch from RSS feeds (real news!)

### Production News Monitoring

For continuous real news monitoring:

```bash
cd /Users/naveenramaka/naveen/ai-hl-processor
python3 news_feed_service.py
```

This monitors:
- Reuters Business News
- Yahoo Finance
- Bloomberg
- NewsAPI (if key is set)

Reports new headlines and analysis results in real-time!

---

## API Testing (Optional)

### REST API

```bash
# Health check
curl http://localhost:8000/health

# Analyze a headline
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Federal Reserve raises interest rates",
    "llm_provider": "mock"
  }'

# View API docs
open http://localhost:8000/docs
```

### WebSocket (Python)

```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8000/ws/stream")
ws.send(json.dumps({
    "headline": "ECB announces bond buying program",
    "llm_provider": "mock"
}))
result = json.loads(ws.recv())
print(result)
ws.close()
```

---

## LLM Provider Options

### Currently Available

**Mock LLM** (Default - No Setup Required)
- ✅ Ready to use immediately
- ✅ Fast (100-200ms)
- ✅ Realistic responses
- ✅ Perfect for testing

### Configure Real LLMs (Optional)

**Google Gemini Flash**:
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CREDENTIALS_PATH="/path/to/service-account.json"
# Then select "Google Gemini Flash" in UI
```

**Anthropic Claude**:
```bash
export ANTHROPIC_API_KEY="your-api-key"
# Then select "Anthropic Claude" in UI
```

---

## Stopping the Services

Press **Ctrl+C** in the terminal where you ran `start_services.py`

Both services will shut down gracefully.

---

## Common Use Cases

### 1. Test Analysis Quality
```bash
# Start services
python3 start_services.py

# Open http://localhost:8501
# Try different headlines in Request/Response tab
# See confidence levels and reasoning
```

### 2. Monitor Live News
```bash
# Terminal 1: Start services
python3 start_services.py

# Terminal 2: Start news monitor
python3 news_feed_service.py

# Watch Terminal 2 for analysis results
```

### 3. Build Custom Integration
```python
import requests

# Analyze headlines from your own news source
headlines = ["Your headline 1", "Your headline 2"]

for headline in headlines:
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"headline": headline, "llm_provider": "mock"}
    )
    result = response.json()
    print(f"{headline[:50]}...")
    for entity in result["impacted_entities"]:
        print(f"  {entity['currency']}: {entity['confidence'].upper()}")
```

---

## Troubleshooting

**Port already in use?**
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>
```

**API not responding?**
```bash
# Check health
curl http://localhost:8000/health

# View logs in terminal where start_services.py is running
```

**Need help?**
- Check `COMPLETE_SETUP_GUIDE.md` for detailed instructions
- Check `SYSTEM_VERIFICATION_REPORT.md` for test results
- Check `REAL_NEWS_SOURCES.md` for news integration help

---

## What's Next?

1. ✅ Test with Mock LLM (you can do this now!)
2. ⏳ Get NewsAPI key for real news (https://newsapi.org/)
3. ⏳ Configure Google Cloud for Gemini Flash (production LLM)
4. ⏳ Monitor real news for 24 hours
5. ⏳ Build your custom integration

---

## Quick Reference

| Task | Command |
|------|---------|
| Start everything | `python3 start_services.py` |
| Open UI | http://localhost:8501 |
| API docs | http://localhost:8000/docs |
| Test simulator | `python3 news_feed_simulator.py` |
| Production monitor | `python3 news_feed_service.py` |
| Stop services | Press Ctrl+C |

---

**You're ready to go! 🚀**

Start with: `python3 start_services.py`

Then open: http://localhost:8501

Happy analyzing! 📰💱
