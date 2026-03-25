# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Real-time semantic analysis system that assesses financial news headline impact on currency markets using Google Gemini Flash (via Vertex AI) with a LangChain agent framework and file-system-based memory for pattern learning.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Single headline analysis (mock LLM, no API calls needed)
python main.py --analyze "Fed raises rates by 25bps" --environment test

# Run demo with 5 headlines
python main.py --demo --environment dev

# Run with real Gemini (requires Google Cloud credentials)
python main.py --analyze "Fed raises rates" --environment uat --json

# Stream mode (requires pipeline services running)
python main.py --stream --environment uat

# Run tests
pytest tests/
pytest --verbose

# Start/stop full pipeline
./scripts/start_all.sh
./scripts/stop_all.sh
./scripts/health_check.sh
```

## Environment Configuration

Set `ENV` in `.env` to one of: `test`, `dev`, `uat`, `prod`

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
Headline → LangChain Agent → Gemini Flash (or Mock) → JSON → Pydantic validation → FileSystemMemory
                ↑
         Memory tools (search similar, currency history, patterns)
```

### Streaming Pipeline

```
RSS Feeds → rss_poller → Input WebSocket (8765) → main.py --stream → Output WebSocket (8766) → file_writer (JSONL)
```

### Key Modules

- **`src/core/analyzer.py`** — `HeadlineImpactAnalyzer`: orchestrates agent + memory; main entry point for analysis
- **`src/core/agent.py`** — LangChain agent factory; returns mock agent (test/dev) or Gemini agent (uat/prod)
- **`src/core/models.py`** — Pydantic models: `Headline`, `CurrencyImpact`, `ImpactAnalysisResult`
- **`src/llm/prompts.py`** — System and user prompts sent to the LLM
- **`src/memory/`** — File-based persistent memory: `file_store.py` (raw storage), `pattern_tracker.py` (learned patterns), `tools.py` (LangChain tools the agent calls)
- **`src/feeds/websocket_adapter.py`** — Async generator that yields headlines from WebSocket stream
- **`services/rss_poller/`** — Polls FT/Reuters RSS feeds, deduplicates by hash, publishes to input WebSocket
- **`services/websocket_servers/`** — Input server (8765) and output server (8766)
- **`services/file_writer/`** — Subscribes to output WebSocket, writes JSONL files

### Configuration

`config.ini` holds environment-specific settings (model, concurrency, rate limits). `src/config/loader.py` parses it into typed dataclasses. `config_loader.py` at root is a legacy loader.

### Memory Store

`memory_store/` directory holds JSON files persisted between runs — past analyses, patterns, and metrics. The agent automatically searches this before making a new assessment.
