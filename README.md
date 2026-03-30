# AI Headline Impact Processor

Analyses financial news headlines in real-time and predicts which currency pairs are impacted, with confidence scores and reasoning. Uses Google Gemini Flash (via Vertex AI) with a memory-enhanced LangChain agent.

Corrections made by users are treated as canonical results. The corrected version is what history renders, what future analysis uses as context, and what gets redistributed to external Kafka consumers.

---

## How it works

```
Source (CSV file or KDB+)
    │  kafka_producer
    ▼
Kafka: raw-headlines
    │  services/server/run_server.py
    ▼
Gemini / Mock LLM  +  memory (past analyses)  +  Redis (impact graph)
    │
    ├──▶  Kafka: headline-impacts   (external consumers + user corrections)
    │
    └──▶  GET /events               (SSE stream → UI)
```

User corrections flow:
```
UI  →  POST /api/corrections
         ├──▶  file store (canonical truth)
         ├──▶  Redis (impact graph updated)
         ├──▶  Kafka: headline-impacts  (type=analysis_corrected)
         └──▶  SSE /events              (UI updates in place)
```

---

## Setup

**Requirements:** Python 3.11+, Docker Desktop, Node 18+

```bash
cd backend
pip3 install -r requirements.txt

cd ../frontend
npm install
```

`.env` for UAT / prod (copy from `.env.example`):
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
```

For `dev` / `test` environments the LLM is mocked — no credentials needed.

---

## Running the pipeline

### 1. Start Kafka

```bash
cd backend
docker compose up -d
```

First run only — create the topics:
```bash
docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic raw-headlines --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 --topic headline-impacts --partitions 3 --replication-factor 1
```

### 2. Start the combined server

```bash
cd backend
python3 services/server/run_server.py --environment dev --port 8080
```

Single process that consumes `raw-headlines` → runs LLM analysis → publishes to `headline-impacts` → serves SSE + REST API on port 8080.

### 3. Start a producer

**From a CSV file** (`headline, source, timestamp` columns — timestamp optional):
```bash
python3 services/kafka_producer/run_producer.py --source file --file data/headlines.csv
```

**From KDB+** (polls every 60s):
```bash
python3 services/kafka_producer/run_producer.py --source kdb --environment uat
```

### 4. Start the UI

```bash
cd frontend
npm run dev    # → http://localhost:5173
```

The frontend dev server proxies `/api`, `/events`, and `/health` to port `8080`. If you run the backend on a different port, update `frontend/vite.config.js`.

### 5. Consume results (external client)

```bash
curl http://localhost:8080/events
```

New analysis event:
```json
{
  "type": "analysis_result",
  "data": {
    "headline": "Federal Reserve raises rates by 75bps",
    "impacted_entities": [
      {"currency": "USD", "confidence": 0.90, "reasoning": "..."},
      {"currency": "EUR", "confidence": 0.75, "reasoning": "..."}
    ],
    "is_corrected": false,
    "processing_time_ms": 1240,
    "model_used": "gemini-2.5-flash-lite"
  }
}
```

User-corrected result (same headline, updated impacts):
```json
{
  "type": "analysis_corrected",
  "data": {
    "headline": "Federal Reserve raises rates by 75bps",
    "impacted_entities": [
      {"currency": "USD", "confidence": 0.65, "reasoning": "..."},
      {"currency": "AUD", "confidence": 0.70, "reasoning": "..."}
    ],
    "is_corrected": true,
    "corrected_by": "reviewer",
    "correction_note": "added AUD impact"
  }
}
```

External consumers distinguish new analyses from corrections via the `type` field.

### Stop everything

```bash
pkill -f "run_server.py"; pkill -f "run_producer.py"
docker compose down
```

---

## One-shot script

```bash
cd backend
./scripts/start_all.sh dev data/headlines.csv   # file source
./scripts/start_all.sh uat                       # kdb source
./scripts/stop_all.sh
./scripts/health_check.sh
```

---

## One-off analysis (no Kafka needed)

```bash
cd backend

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

Edit `backend/config.ini` or set env vars:

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
backend/
  main.py                         # --analyze / --demo (CLI testing only)
  config.ini                      # all environment config
  docker-compose.yml              # local Kafka + Zookeeper

  src/
    config/loader.py              # typed config dataclasses
    core/
      models.py                   # Headline, CurrencyImpact, ImpactAnalysisResult
      agent.py                    # LangChain agent (Gemini or mock)
      analyzer.py                 # orchestrates agent + memory per headline
    llm/
      prompts.py                  # system + user prompts
      client_factory.py           # returns correct agent for environment
    memory/
      file_store.py               # persists analyses, Jaccard similarity search
      redis_store.py              # Redis dedup cache + per-currency impact graph
      pattern_tracker.py          # event-currency pattern learning
    feeds/
      kafka_adapter.py            # consumes raw-headlines → Headline objects
    sources/
      file_source.py              # CSV, rate-limited
      kdb_source.py               # qpython poll + SHA-256 dedup

  services/
    server/
      server.py                   # FastAPI: analyzer loop + SSE stream + REST API
      run_server.py               # entry point: uvicorn on --port
    kafka_producer/
      producer_service.py         # HeadlineSource → Kafka topic
      run_producer.py             # entry point: --source file|kdb

  scripts/
    start_all.sh                  # start Kafka + server + producer
    stop_all.sh                   # stop all services
    health_check.sh               # check service status + HTTP health

frontend/
  src/
    components/                   # Dashboard, LiveFeed, History, Insights,
                                  # Corrections, EndOfDay
    hooks/                        # useSSE, usePolling
    api/client.js                 # REST API calls
  vite.config.js                  # proxies /api /events /health → :8080
```

Additional design notes:

- `HEADLINE_EVENT_HANDLING.md` — live feed, history, duplicates, and canonical correction behavior
- `KNOWLEDGE_GRAPH_DESIGN.md` — proposed fast/slow loop and knowledge-graph direction

---

## Adding a new headline source

1. Create `src/sources/my_source.py` implementing `HeadlineSource` (`connect`, `disconnect`, `stream_headlines`, `is_connected`)
2. Add an `elif args.source == 'mysource':` branch in `services/kafka_producer/run_producer.py`
3. Add any config to `config.ini` and expose it via `src/config/loader.py`

Nothing else changes.
