# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Real-time semantic analysis system that assesses financial news headline impact on currency markets using Google Gemini Flash (via Vertex AI) with a LangChain agent framework, file-system memory for pattern learning, and a Redis-backed currency impact graph.

## Project Structure

```
ai-hl-processor/
├── backend/          ← all Python server code (run commands from here)
│   ├── main.py
│   ├── requirements.txt
│   ├── config.ini
│   ├── src/          (config, core, feeds, llm, memory, sources)
│   ├── services/     (kafka_producer, sse_server)
│   ├── tests/
│   ├── scripts/
│   └── data/
└── frontend/         ← React/Vite UI (npm commands from here)
```

## Commands

All Python commands run from `backend/`:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Single headline analysis (mock LLM, no API calls needed)
python3 main.py --analyze "Fed raises rates by 25bps" --environment test

# Run demo with 5 headlines
python3 main.py --demo --environment dev

# Run with real Gemini (requires Google Cloud credentials)
python3 main.py --analyze "Fed raises rates" --environment uat --json

# Stream mode (Kafka consumer → analyzer → Kafka producer)
python3 main.py --stream --environment uat

# SSE server (REST API + SSE stream on port 8080)
python3 services/sse_server/run_sse.py --port 8080 --environment dev

# Kafka producer (feed headlines from file or KDB+)
python3 services/kafka_producer/run_producer.py --source file --file data/headlines.csv
python3 services/kafka_producer/run_producer.py --source kdb --environment uat

# Run tests
python3 -m pytest tests/ -v

# Start/stop full pipeline
./scripts/start_all.sh [environment] [csv_file]
./scripts/stop_all.sh
./scripts/health_check.sh
```

Frontend (from `frontend/`):
```bash
cd frontend
npm install
npm run dev      # → http://localhost:5173
npm run build    # production build → frontend/dist/
```

## Environment Configuration

Set `ENV` in `backend/.env` to one of: `test`, `dev`, `uat`, `prod`

| ENV  | LLM Provider | Notes |
|------|-------------|-------|
| test | mock_llm    | Instant, no API calls |
| dev  | mock_llm    | Debug logging |
| uat  | gemini_flash | Requires Google Cloud credentials |
| prod | gemini_flash | Rate-limited (300 rpm) |

Required env vars for uat/prod:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account-key.json
```

## Architecture

### Data Flow

```
HeadlineSource (CSV/KDB+)
    → Kafka (raw-headlines)
    → main.py --stream
    → HeadlineImpactAnalyzer
        → LangChain Agent (Gemini Flash or Mock)
        → FileSystemMemory (Jaccard similarity, pattern learning)
        → RedisImpactStore (dedup cache + per-currency impact graph)
    → Kafka (headline-impacts)
    → SSE Server (/events stream + /api/* REST endpoints)
    → React UI (frontend/)
```

### Key Modules

- **`backend/src/core/analyzer.py`** — `HeadlineImpactAnalyzer`: orchestrates agent + memory + Redis writes
- **`backend/src/core/agent.py`** — LangChain agent factory; enriches prompts with file memory + Redis context
- **`backend/src/core/models.py`** — Pydantic models: `Headline`, `CurrencyImpact`, `ImpactAnalysisResult`
- **`backend/src/memory/file_store.py`** — JSON file store for persistent analysis history
- **`backend/src/memory/redis_store.py`** — Redis dedup cache + per-currency sorted-set impact graph
- **`backend/src/memory/pattern_tracker.py`** — Learned keyword→currency correlation patterns
- **`backend/services/sse_server/sse_server.py`** — FastAPI: SSE stream + REST API endpoints
- **`backend/services/kafka_producer/`** — Source-agnostic headline publisher (file/KDB+)

### Configuration

`backend/config.ini` holds environment-specific settings. `backend/src/config/loader.py` parses it into typed dataclasses.

### Memory Store

`backend/memory_store/` — JSON files persisted between runs (analyses, patterns, metrics, corrections).

## Testing

When writing tests, always check Pydantic model validation constraints before writing fixtures:
- `CurrencyImpact.reasoning` requires `min_length=10`
- `CurrencyImpact.confidence` must be 0.0–1.0
