# AI Headline Impact Processor

Real-time financial headline analysis system. Headlines flow from a source (CSV file or KDB+) into Kafka, get analysed by a LangChain + Gemini agent for currency impact, and results are streamed to consumers via SSE.

## Architecture

```
Source (CSV / KDB+)
        │
        ▼
 kafka_producer  ──►  Kafka: raw-headlines
                               │
                               ▼
                          main.py --stream   (HeadlineImpactAnalyzer + Gemini / Mock LLM)
                               │
                               ▼
                       Kafka: headline-impacts
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              SSE /events          downstream consumers
         (http://localhost:8080)
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Docker Desktop | any recent |
| Google Cloud project + Vertex AI | UAT / prod only |

---

## First-time setup

```bash
# 1. Install Python dependencies
pip3 install -r requirements.txt

# 2. Copy env file and fill in your Google Cloud credentials (UAT/prod only)
cp .env.example .env
```

`.env` keys:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
ENV=dev                          # test | dev | uat | prod
```

For `test` / `dev` environments the LLM is mocked — no Google Cloud credentials needed.

---

## Environments

| ENV  | LLM | Notes |
|------|-----|-------|
| `test` | mock (keyword match) | No API calls, instant |
| `dev`  | mock | Debug logging |
| `uat`  | Gemini Flash (real) | Needs GCP credentials |
| `prod` | Gemini Flash (real) | Rate-limited, full observability |

---

## Running the pipeline

### Step 1 — Start Kafka

```bash
docker compose up -d
```

Wait ~10 seconds for the broker to be healthy, then create topics (first run only):

```bash
docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic raw-headlines --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic headline-impacts --partitions 3 --replication-factor 1
```

Verify:
```bash
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

### Step 2 — Start the Analyzer

Consumes `raw-headlines`, runs LLM analysis, publishes results to `headline-impacts`.

```bash
python3 main.py --stream --environment dev
```

Logs to stdout. Leave this running in its own terminal.

---

### Step 3 — Start the SSE Server

Consumes `headline-impacts` and fans results out to SSE clients.

```bash
python3 services/sse_server/run_sse.py --environment dev --port 8080
```

Endpoints:
- `GET http://localhost:8080/events` — SSE stream
- `GET http://localhost:8080/health` — health check + connected client count

---

### Step 4 — Start a Producer

#### From a CSV file

CSV must have columns: `headline, source, timestamp`
`timestamp` is optional (ISO-8601, defaults to now).
Rate: 1 headline/second by default (configurable via `file_source_rate_per_second` in `config.ini`).

```bash
python3 services/kafka_producer/run_producer.py \
  --source file \
  --file data/headlines.csv \
  --environment dev
```

A sample file is at `data/headlines.csv`.

#### From KDB+

Polls KDB+ every 60 seconds. Configure connection in `config.ini` under `[kdb]` or via env vars:

```bash
export KDB_HOST=localhost
export KDB_PORT=5000

python3 services/kafka_producer/run_producer.py \
  --source kdb \
  --environment uat
```

KDB config in `config.ini`:
```ini
[kdb]
host = localhost
port = 5000
query = select text, source, time from headlines where date=.z.d
poll_interval_seconds = 60
```

---

### Step 5 — Consume the SSE stream

```bash
curl http://localhost:8080/events
```

Each event looks like:
```
data: {"type": "analysis_result", "timestamp": "...", "data": {
         "headline": "Federal Reserve raises rates by 75bps",
         "impacted_entities": [
           {"currency": "USD", "confidence": 0.9, "reasoning": "..."},
           {"currency": "EUR", "confidence": 0.75, "reasoning": "..."}
         ],
         "processing_time_ms": 1240,
         "model_used": "gemini-2.5-flash-lite"
       }}
```

---

## One-shot script (file source)

```bash
# Starts Kafka (Docker), analyzer, SSE server, and file producer in one go
./scripts/start_all.sh dev data/headlines.csv

# KDB source
./scripts/start_all.sh uat
```

Stop everything:
```bash
pkill -f "main.py --stream"
pkill -f "run_sse.py"
pkill -f "run_producer.py"
docker compose down
```

---

## One-off headline analysis (no Kafka)

```bash
# Single headline, mock LLM
python3 main.py --analyze "ECB cuts rates by 50bps" --environment dev

# JSON output
python3 main.py --analyze "ECB cuts rates by 50bps" --environment dev --json

# 5 demo headlines
python3 main.py --demo --environment dev
```

---

## Project structure

```
main.py                          # Analyzer entry point (--analyze / --demo / --stream)
config.ini                       # All environment config
docker-compose.yml               # Kafka + Zookeeper

src/
  core/
    analyzer.py                  # HeadlineImpactAnalyzer — orchestrates agent + memory
    agent.py                     # LangChain agent (mock or Gemini)
    models.py                    # Pydantic models: Headline, CurrencyImpact, ImpactAnalysisResult
  llm/
    prompts.py                   # System + user prompts
    client_factory.py            # Returns mock or Gemini agent based on environment
  memory/
    file_store.py                # Persists analyses to memory_store/, Jaccard similarity search
    pattern_tracker.py           # Learns event-currency patterns across history
  sources/
    base.py                      # HeadlineSource ABC
    file_source.py               # CSV reader with rate limiting
    kdb_source.py                # qpython KDB+ poller with deduplication
  feeds/
    kafka_adapter.py             # KafkaFeedAdapter — consumes raw-headlines → Headline objects
  config/
    loader.py                    # Typed config dataclasses; get_feed_config(), get_kdb_config()

services/
  kafka_producer/
    producer_service.py          # KafkaProducerService: any HeadlineSource → Kafka topic
    run_producer.py              # Entry point: --source file|kdb
  sse_server/
    sse_server.py                # FastAPI SSE app, per-client asyncio.Queue fan-out
    run_sse.py                   # Entry point: uvicorn on port 8080

data/
  headlines.csv                  # Sample headlines for testing

logs/                            # Runtime logs (gitignored)
memory_store/                    # Persisted LLM analyses (gitignored)
```

---

## Adding a new headline source

1. Create `src/sources/my_source.py` implementing `HeadlineSource` (connect / disconnect / stream_headlines / is_connected)
2. Add a new `elif args.source == 'mysource':` branch in `services/kafka_producer/run_producer.py`
3. Add any config it needs to `config.ini` and `src/config/loader.py`

The analyzer, SSE server, and everything downstream needs no changes.
