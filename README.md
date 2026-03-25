# AI Headline Impact Processor

Analyses financial news headlines in real-time and predicts which currency pairs are impacted, with confidence scores and reasoning. Uses Google Gemini Flash (via Vertex AI) with a memory-enhanced LangChain agent.

---

## How it works

```
Source (CSV file or KDB+)
    │  kafka_producer
    ▼
Kafka: raw-headlines
    │  main.py --stream
    ▼
Gemini / Mock LLM  +  memory (past analyses)
    │
    ▼
Kafka: headline-impacts
    │  sse_server
    ▼
GET /events  (SSE stream → UI / downstream consumers)
```

---

## Setup

**Requirements:** Python 3.11+, Docker Desktop

```bash
pip3 install -r requirements.txt
cp .env.example .env          # add Google Cloud credentials for uat/prod
```

`.env` for UAT / prod:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
```

For `dev` / `test` environments the LLM is mocked — no credentials needed.

---

## Running the pipeline

### 1. Start Kafka

```bash
docker compose up -d
```

First run only — create the topics:
```bash
docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic raw-headlines --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic headline-impacts --partitions 3 --replication-factor 1
```

### 2. Start the analyzer

```bash
python3 main.py --stream --environment dev
```

Consumes `raw-headlines` → runs LLM → publishes to `headline-impacts`.

### 3. Start the SSE server

```bash
python3 services/sse_server/run_sse.py --environment dev --port 8080
```

### 4. Start a producer

**From a CSV file** (`headline, source, timestamp` columns — timestamp optional):
```bash
python3 services/kafka_producer/run_producer.py --source file --file data/headlines.csv
```

**From KDB+** (polls every 60s):
```bash
python3 services/kafka_producer/run_producer.py --source kdb --environment uat
```

### 5. Consume results

```bash
curl http://localhost:8080/events
```

Each event:
```json
data: {
  "type": "analysis_result",
  "data": {
    "headline": "Federal Reserve raises rates by 75bps",
    "impacted_entities": [
      {"currency": "USD", "confidence": 0.90, "reasoning": "..."},
      {"currency": "EUR", "confidence": 0.75, "reasoning": "..."}
    ],
    "processing_time_ms": 1240,
    "model_used": "gemini-2.5-flash-lite"
  }
}
```

### Stop everything

```bash
pkill -f "main.py --stream"; pkill -f "run_sse.py"; pkill -f "run_producer.py"
docker compose down
```

---

## One-shot script

```bash
./scripts/start_all.sh dev data/headlines.csv   # file source
./scripts/start_all.sh uat                       # kdb source
```

---

## One-off analysis (no Kafka needed)

```bash
# Single headline
python3 main.py --analyze "ECB cuts rates by 50bps" --environment dev

# JSON output
python3 main.py --analyze "ECB cuts rates by 50bps" --environment dev --json

# 5 demo headlines
python3 main.py --demo --environment dev
```

---

## Environments

| ENV | LLM | Use for |
|-----|-----|---------|
| `test` | mock | CI, fast checks |
| `dev` | mock | local development |
| `uat` | Gemini Flash | pre-prod validation |
| `prod` | Gemini Flash | production |

---

## KDB+ configuration

Edit `config.ini` or set env vars:

```ini
[kdb]
host = localhost
port = 5000
query = select text, source, time from headlines where date=.z.d
poll_interval_seconds = 60
```

Env var overrides: `KDB_HOST`, `KDB_PORT`, `KDB_USERNAME`, `KDB_PASSWORD`

---

## Project structure

```
main.py                         # --analyze / --demo / --stream
config.ini                      # all environment config
docker-compose.yml              # local Kafka + Zookeeper

src/
  config/loader.py              # typed config, get_feed_config(), get_kdb_config()
  core/
    models.py                   # Headline, CurrencyImpact, ImpactAnalysisResult
    agent.py                    # LangChain agent (Gemini or mock)
    analyzer.py                 # orchestrates agent + memory per headline
  llm/
    prompts.py                  # system + user prompts
    client_factory.py           # returns correct agent for environment
  memory/
    file_store.py               # persists analyses, Jaccard similarity search
    pattern_tracker.py          # event-currency pattern learning
    tools.py                    # LangChain memory tools
  feeds/
    base.py                     # FeedAdapter ABC
    kafka_adapter.py            # consumes raw-headlines → Headline objects
  sources/
    base.py                     # HeadlineSource ABC
    file_source.py              # CSV, rate-limited (1/sec)
    kdb_source.py               # qpython poll + SHA-256 dedup

services/
  kafka_producer/
    producer_service.py         # HeadlineSource → Kafka topic
    run_producer.py             # entry point: --source file|kdb
  sse_server/
    sse_server.py               # FastAPI SSE, per-client queue fan-out
    run_sse.py                  # entry point: uvicorn on --port

scripts/
  start_all.sh                  # start all services
  stop_all.sh                   # stop all services
  health_check.sh               # check service status
```

---

## Adding a new headline source

1. Create `src/sources/my_source.py` implementing `HeadlineSource` (`connect`, `disconnect`, `stream_headlines`, `is_connected`)
2. Add an `elif args.source == 'mysource':` branch in `services/kafka_producer/run_producer.py`
3. Add any config to `config.ini` and expose it via `src/config/loader.py`

Nothing else changes.
