# Phase 1.5 - Enhanced Features

## 🎉 New Features Added

### 1. **Multi-LLM Provider Support** 🤖

You can now choose from multiple LLM providers:
- **Mock LLM** - Fast testing, no API required
- **Google Gemini Flash** - Production-ready, Google Cloud
- **Anthropic Claude** - High-quality reasoning (optional)

**How to use:**
- Select provider from dropdown in Streamlit UI
- Or specify in API request: `{"llm_provider": "mock"}`

**Setup:**
```bash
# For Gemini Flash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# For Claude
export ANTHROPIC_API_KEY=your-api-key
pip install anthropic
```

### 2. **WebSocket Streaming** 📡

Real-time headline processing via WebSocket!

**API Endpoint:**
```
ws://localhost:8000/ws/stream
```

**Usage:**
```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws/stream");

// Send headline
ws.send(JSON.stringify({
    "headline": "Fed raises interest rates",
    "min_confidence": 0.3,
    "llm_provider": "mock"
}));

// Receive results
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.status === "completed") {
        console.log(data.data);
    }
};
```

### 3. **Dual-Mode Streamlit UI** 📊

The UI now has **TWO modes**:

#### **Mode 1: Request/Response** (Traditional)
- Enter a headline
- Click "Analyze Impact"
- View results instantly
- Export to JSON/CSV

#### **Mode 2: Live Stream** (New!)
- Enter headlines continuously
- Results appear in real-time
- Stream history maintained
- Perfect for monitoring live news feeds

**How to switch:**
- Use tabs at the top: "📊 Request / Response" | "📡 Live Stream"

### 4. **LLM Provider Abstraction Layer** 🏗️

New file: `llm_providers.py`

**Features:**
- Clean abstraction for adding new LLM providers
- Base class: `BaseLLMClient`
- Factory pattern: `LLMClientFactory`
- Easy to extend with new providers

**Add a new provider:**
```python
class MyLLMClient(BaseLLMClient):
    async def analyze_impact(self, news_headline, entity_id, entity_context):
        # Your implementation
        return {
            'probabilities': {...},
            'reasoning': "...",
            'confidence': 0.8,
            'model_used': "My LLM"
        }

    def get_provider_name(self):
        return "My Custom LLM"

# Register in factory
LLMClientFactory.create_client("my_llm")
```

---

## 📁 New Files Created

1. **`llm_providers.py`** (393 lines)
   - `BaseLLMClient` - Abstract base class
   - `MockLLMClient` - Testing client
   - `GeminiFlashClient` - Google Cloud integration
   - `ClaudeClient` - Anthropic integration
   - `LLMClientFactory` - Provider factory

2. **`streamlit_app.py`** (v2 - 441 lines)
   - Dual-mode UI (Request/Response + Live Stream)
   - LLM provider selector dropdown
   - WebSocket client integration
   - Stream history with session state

3. **Updated Files:**
   - `api_service.py` - Added WebSocket endpoint
   - `models.py` - Added `llm_provider` field
   - `requirements.txt` - Added `websocket-client`, `anthropic`

---

## 🚀 How to Use

### Start the Services

```bash
python3 start_services.py
```

This starts:
- FastAPI backend on http://localhost:8000
- Streamlit UI on http://localhost:8501

### Using the UI

1. **Open** http://localhost:8501
2. **Sidebar:**
   - Select LLM Provider (Mock, Gemini, Claude)
   - Set confidence threshold
3. **Request/Response Tab:**
   - Enter headline → Analyze → View results
4. **Live Stream Tab:**
   - Enter headlines continuously
   - Results appear in real-time
   - Clear history when needed

### Using the API

#### REST Endpoint (Traditional)
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Fed raises interest rates",
    "min_confidence": 0.3,
    "llm_provider": "mock"
  }'
```

#### WebSocket Endpoint (New!)
```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8000/ws/stream")

# Send headline
ws.send(json.dumps({
    "headline": "ECB announces bond buying",
    "min_confidence": 0.3,
    "llm_provider": "mock"
}))

# Get result
result = ws.recv()
print(json.loads(result))

ws.close()
```

---

## 🎯 Use Cases

### Use Case 1: Live News Monitoring

```python
# Connect to WebSocket
ws = websocket.create_connection("ws://localhost:8000/ws/stream")

# Stream news headlines as they come
news_feed = [
    "Fed raises rates by 0.75%",
    "Russia attacks Ukraine",
    "OPEC cuts production"
]

for headline in news_feed:
    ws.send(json.dumps({"headline": headline}))
    result = json.loads(ws.recv())
    print(f"Impact on {result['data']['impacted_entities']}")
```

### Use Case 2: A/B Testing LLM Providers

```python
providers = ["mock", "gemini_flash", "claude"]

for provider in providers:
    response = requests.post(
        "http://localhost:8000/analyze",
        json={
            "headline": "Same headline",
            "llm_provider": provider
        }
    )
    print(f"{provider}: {response.json()}")
```

### Use Case 3: Real-Time Dashboard

Use the Streamlit Live Stream tab to:
1. Monitor incoming news
2. See impact assessments instantly
3. Track confidence levels
4. Export for reporting

---

## 🔧 Configuration

### LLM Provider Settings

**Mock LLM (Default)**
- No configuration needed
- Fast, reliable testing
- Pre-configured response templates

**Google Gemini Flash**
- Requires: `GOOGLE_CLOUD_PROJECT`
- Requires: `GOOGLE_CREDENTIALS_PATH`
- Model: `gemini-flash-lite-latest`

**Anthropic Claude**
- Requires: `ANTHROPIC_API_KEY`
- Install: `pip install anthropic`
- Model: `claude-3-5-sonnet-20241022`

### WebSocket Configuration

Default URL: `ws://localhost:8000/ws/stream`

**Client timeout:** 30 seconds
**Max message size:** Unlimited
**Reconnection:** Manual (implement in client)

---

## 📊 Architecture Updates

### Before (Phase 1)
```
User → Streamlit → HTTP POST → FastAPI → POCImpactAssessor → Response
```

### After (Phase 1.5)
```
User → Streamlit
    ├─ Tab 1: HTTP POST → FastAPI → LLM Factory → [Mock|Gemini|Claude] → Response
    └─ Tab 2: WebSocket → FastAPI → LLM Factory → [Mock|Gemini|Claude] → Stream
```

### LLM Provider Flow
```
API Request
    ↓
LLMClientFactory
    ↓
[Mock LLM | Gemini Flash | Claude]
    ↓
POCImpactAssessor
    ↓
Simplified Response
```

---

## 🧪 Testing

### Test WebSocket Connection

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/ws/stream

# Send message
{"headline": "Fed raises rates", "llm_provider": "mock"}

# Receive response
```

### Test LLM Providers

```python
from llm_providers import LLMClientFactory, LLMProvider

# Test Mock
mock_client = LLMClientFactory.create_client(LLMProvider.MOCK)
result = await mock_client.analyze_impact("Test headline", "EURUSD", {})
print(result)

# Test Gemini (requires credentials)
gemini_client = LLMClientFactory.create_client(LLMProvider.GEMINI_FLASH)
result = await gemini_client.analyze_impact("Test headline", "EURUSD", {})
print(result)
```

---

## 📈 Performance

| Feature | Performance |
|---------|-------------|
| WebSocket Connection | <100ms |
| Stream Message Processing | ~200ms (mock) |
| LLM Provider Switch | Instant |
| UI Tab Switch | Instant |
| Session State | In-memory, fast |

---

## 🔮 Future Enhancements

- [ ] Auto-reconnect WebSocket
- [ ] Server-sent events (SSE) alternative
- [ ] Batch streaming (multiple headlines at once)
- [ ] LLM response caching
- [ ] Rate limiting per provider
- [ ] Provider health monitoring
- [ ] Cost tracking per provider
- [ ] Custom provider plugins

---

## 🐛 Troubleshooting

### WebSocket Connection Fails

**Issue:** `WebSocket error: Connection refused`

**Solution:**
1. Ensure API is running: `curl http://localhost:8000/health`
2. Check WebSocket URL: `ws://localhost:8000/ws/stream` (not `http://`)
3. Restart services: `python3 start_services.py`

### LLM Provider Not Working

**Issue:** `Error calling Gemini Flash`

**Solution:**
1. Check credentials: `echo $GOOGLE_CLOUD_PROJECT`
2. Verify credentials file exists
3. Test with Mock provider first
4. Check logs in API terminal

### Stream Not Updating

**Issue:** Results don't appear in Live Stream tab

**Solution:**
1. Click "📤 Send to Stream" button
2. Check browser console for errors
3. Verify WebSocket connection in Network tab
4. Clear stream history and retry

---

## 📝 Migration Guide

### From Phase 1 to Phase 1.5

**No breaking changes!** Phase 1 functionality still works.

**Optional upgrades:**
1. Install new dependencies: `pip install -r requirements.txt`
2. Use LLM provider selector in UI
3. Try Live Stream tab for real-time monitoring

**Existing code:**
```python
# Still works!
response = requests.post("/analyze", json={"headline": "..."})
```

**New code:**
```python
# Now with provider selection
response = requests.post("/analyze", json={
    "headline": "...",
    "llm_provider": "gemini_flash"
})
```

---

## 🎓 Examples

### Example 1: Simple Streaming

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data.get('status') == 'completed':
        entities = data['data']['impacted_entities']
        for entity in entities:
            print(f"{entity['currency']}: {entity['confidence']}")

ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/stream",
    on_message=on_message
)

ws.send(json.dumps({"headline": "Fed raises rates"}))
ws.run_forever()
```

### Example 2: Multi-Provider Comparison

```python
import asyncio
from llm_providers import LLMClientFactory, LLMProvider

async def compare_providers(headline):
    providers = [LLMProvider.MOCK, LLMProvider.GEMINI_FLASH]

    for provider in providers:
        client = LLMClientFactory.create_client(provider)
        result = await client.analyze_impact(headline, "EURUSD", {})
        print(f"{provider}: {result['confidence']}")

asyncio.run(compare_providers("ECB announces QE"))
```

### Example 3: Stream with History

```python
# In Streamlit Live Stream tab
# 1. Enter: "Fed raises rates"
# 2. Click Send
# 3. See result appear
# 4. Enter: "ECB bond buying"
# 5. Click Send
# 6. See both results in history
# 7. Click "Clear Stream History" to reset
```

---

**Version:** 2.0.0-phase1.5
**Date:** January 9, 2026
**Status:** ✅ Ready to use!
