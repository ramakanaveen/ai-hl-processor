# RSS Feed to WebSocket Pipeline Guide

## Overview

The RSS-to-WebSocket pipeline provides an event-driven architecture for processing financial news headlines in real-time. The system is designed to be extensible, allowing you to add multiple feed sources (RSS, Bloomberg, KDB, etc.) without modifying the analyzer.

## Architecture

```
RSS Poller → Input WebSocket (8765) → Analyzer → Output WebSocket (8766) → File Writer
(separate)   (headlines bus)            (main.py)   (results bus)             (consumer)
```

### Components

1. **Input WebSocket Server (port 8765)**: Receives headlines from all feed sources
2. **Output WebSocket Server (port 8766)**: Broadcasts analysis results to consumers
3. **RSS Feed Poller**: Polls RSS feeds and publishes to input WebSocket
4. **Analyzer (Stream Mode)**: Processes headlines using LangChain agent with memory
5. **File Writer**: Subscribes to output WebSocket and writes results to files

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start All Services

```bash
./scripts/start_all.sh
```

This will start all 5 services in the background with logs in the `logs/` directory.

### 3. Check Service Health

```bash
./scripts/health_check.sh
```

You should see all services running:
```
✓ Input WebSocket Server (port 8765): RUNNING
✓ Output WebSocket Server (port 8766): RUNNING
✓ RSS Feed Poller: RUNNING
✓ Analyzer (stream mode): RUNNING
✓ File Writer Service: RUNNING
```

### 4. Monitor Output

Watch results being written to files:
```bash
tail -f output/results/results_*.jsonl
```

### 5. Stop All Services

```bash
./scripts/stop_all.sh
```

## Configuration

### RSS Feeds

Edit `services/rss_poller/config.yaml` to add/modify RSS feeds:

```yaml
feeds:
  - name: "Financial Times World"
    url: "https://www.ft.com/world?format=rss"
    poll_interval_seconds: 60

  - name: "Reuters Business"
    url: "https://www.reuters.com/business/rss"
    poll_interval_seconds: 30
```

### WebSocket URLs

Edit `config.ini` to change WebSocket server URLs:

```ini
[feeds]
input_websocket_url = ws://localhost:8765
output_websocket_url = ws://localhost:8766
```

### File Writer

Edit `services/file_writer/config.yaml` to configure output:

```yaml
output:
  format: "jsonl"  # or "json"
  directory: "output/results"
  file_pattern: "results_{date}.jsonl"

  rotation:
    enabled: true
    max_size_mb: 100
```

## Running Services Individually

### Input WebSocket Server
```bash
cd services/websocket_servers
python3 run_input_server.py
```

### Output WebSocket Server
```bash
cd services/websocket_servers
python3 run_output_server.py
```

### RSS Feed Poller
```bash
cd services/rss_poller
python3 run_poller.py
```

### Analyzer (Stream Mode)
```bash
python3 main.py --stream --environment test
```

Options:
- `--environment`: test, dev, uat, or prod
- `--input-ws`: Override input WebSocket URL
- `--output-ws`: Override output WebSocket URL

### File Writer
```bash
cd services/file_writer
python3 run_writer.py
```

## Message Formats

### Input Messages (Headlines)

Published to input WebSocket (port 8765):

```json
{
  "type": "headline",
  "timestamp": "2026-01-13T10:30:00.000Z",
  "data": {
    "text": "Federal Reserve raises interest rates by 0.75%",
    "source": "Financial Times World",
    "link": "https://ft.com/content/...",
    "published": "2026-01-13T10:25:00.000Z",
    "guid": "a1b2c3d4e5f6g7h8",
    "metadata": {
      "author": "John Doe",
      "summary": "The Federal Reserve..."
    }
  }
}
```

### Output Messages (Analysis Results)

Published to output WebSocket (port 8766):

```json
{
  "type": "analysis_result",
  "timestamp": "2026-01-13T10:30:05.234Z",
  "data": {
    "headline": "Federal Reserve raises interest rates by 0.75%",
    "timestamp": "2026-01-13T10:30:05.000Z",
    "impacted_entities": [
      {
        "currency": "USD",
        "confidence": 0.92,
        "reasoning": "Rate hikes typically strengthen the dollar..."
      }
    ],
    "processing_time_ms": 1234.56,
    "model_used": "gemini-2.5-flash-lite",
    "error": null
  }
}
```

## Testing the Pipeline

### 1. Test WebSocket Servers

Test input server:
```python
import asyncio
import websockets
import json
from datetime import datetime

async def test_input():
    async with websockets.connect('ws://localhost:8765') as ws:
        msg = {
            'type': 'headline',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'text': 'Test: Fed raises rates by 0.75%',
                'source': 'test',
                'link': 'http://test.com',
                'published': datetime.now().isoformat(),
                'guid': 'test-123'
            }
        }
        await ws.send(json.dumps(msg))
        print('Sent test headline')

asyncio.run(test_input())
```

Monitor output server:
```python
import asyncio
import websockets

async def monitor_output():
    async with websockets.connect('ws://localhost:8766') as ws:
        async for message in ws:
            print('Received:', message)

asyncio.run(monitor_output())
```

### 2. Test Individual Components

Test RSS poller:
```bash
cd services/rss_poller
python3 rss_feed_poller.py
```

Test analyzer:
```bash
python3 main.py --analyze "Fed raises interest rates by 0.75%"
```

Test file writer:
```bash
cd services/file_writer
python3 file_writer_service.py
```

## Logs

All service logs are stored in the `logs/` directory:
- `input_ws.log`: Input WebSocket server
- `output_ws.log`: Output WebSocket server
- `rss_poller.log`: RSS feed poller
- `analyzer.log`: Analyzer (stream mode)
- `file_writer.log`: File writer service

Tail logs in real-time:
```bash
tail -f logs/*.log
```

## Extending the Pipeline

### Adding a New Feed Source (e.g., Bloomberg)

1. Create a new poller service:
```bash
mkdir -p services/bloomberg_poller
```

2. Implement the poller to publish to input WebSocket (port 8765):
```python
import websockets
import json
from datetime import datetime

async def publish_headline(headline_text):
    async with websockets.connect('ws://localhost:8765') as ws:
        msg = {
            'type': 'headline',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'text': headline_text,
                'source': 'bloomberg',
                'link': '...',
                'published': datetime.now().isoformat(),
                'guid': '...'
            }
        }
        await ws.send(json.dumps(msg))
```

3. No changes needed to analyzer or other services!

### Adding a New Consumer (e.g., Dashboard)

1. Create a new consumer service
2. Subscribe to output WebSocket (port 8766)
3. Process analysis results as needed

Example:
```python
import websockets
import json

async def dashboard_consumer():
    async with websockets.connect('ws://localhost:8766') as ws:
        async for message in ws:
            data = json.loads(message)
            if data.get('type') == 'analysis_result':
                # Update dashboard with result
                update_dashboard(data['data'])
```

## Troubleshooting

### Services Won't Start

Check if ports are already in use:
```bash
lsof -i :8765  # Input WebSocket
lsof -i :8766  # Output WebSocket
```

### No Headlines Appearing

1. Check RSS poller logs:
```bash
tail -f logs/rss_poller.log
```

2. Verify RSS feeds are accessible:
```bash
curl -I https://www.ft.com/world?format=rss
```

3. Check deduplication file:
```bash
cat services/rss_poller/seen_headlines.json
```

### Analyzer Not Processing

1. Check analyzer logs:
```bash
tail -f logs/analyzer.log
```

2. Verify LLM configuration:
```bash
python3 -c "from src.config.loader import get_config; config = get_config('test'); print(config.model_config.use_mock_llm)"
```

### File Writer Not Writing

1. Check file writer logs:
```bash
tail -f logs/file_writer.log
```

2. Verify output directory exists:
```bash
ls -la output/results/
```

## Performance Tuning

### Increase Concurrency

Edit `config.ini`:
```ini
[test]
max_concurrent_llm_calls = 5  # Increase for more parallelism
```

### Adjust RSS Polling Intervals

Edit `services/rss_poller/config.yaml`:
```yaml
feeds:
  - name: "Financial Times World"
    poll_interval_seconds: 30  # Poll more frequently
```

### File Rotation

Edit `services/file_writer/config.yaml`:
```yaml
rotation:
  enabled: true
  max_size_mb: 50  # Rotate at 50MB instead of 100MB
```

## Production Deployment

### 1. Use Production Environment

```bash
python3 main.py --stream --environment prod
```

### 2. Use Process Manager (supervisord)

Create `/etc/supervisor/conf.d/headline-analyzer.conf`:
```ini
[program:input_websocket]
command=python3 run_input_server.py
directory=/path/to/ai-hl-processor/services/websocket_servers
autostart=true
autorestart=true

[program:output_websocket]
command=python3 run_output_server.py
directory=/path/to/ai-hl-processor/services/websocket_servers
autostart=true
autorestart=true

[program:rss_poller]
command=python3 run_poller.py
directory=/path/to/ai-hl-processor/services/rss_poller
autostart=true
autorestart=true

[program:analyzer]
command=python3 main.py --stream --environment prod
directory=/path/to/ai-hl-processor
autostart=true
autorestart=true

[program:file_writer]
command=python3 run_writer.py
directory=/path/to/ai-hl-processor/services/file_writer
autostart=true
autorestart=true
```

### 3. Set Up Monitoring

Use Prometheus metrics (already configured in `config.ini`):
```ini
[prod]
prometheus_enabled = true
```

### 4. Configure Google Cloud Credentials

Create `.env` file:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account-key.json
ENV=prod
```

## Next Steps

1. **Add More RSS Feeds**: Edit `services/rss_poller/config.yaml`
2. **Implement Bloomberg Adapter**: Create `services/bloomberg_poller/`
3. **Add Real-Time Dashboard**: Create consumer for output WebSocket
4. **Set Up Alerting**: Monitor critical errors in logs
5. **Scale Horizontally**: Run multiple analyzer instances with load balancer

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run health check: `./scripts/health_check.sh`
3. Review configuration in `config.ini`
