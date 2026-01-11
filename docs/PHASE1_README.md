# Phase 1: FastAPI + Streamlit Architecture

## Overview

Phase 1 introduces a modern web-based architecture with:
- **FastAPI Backend**: REST API for news analysis
- **Streamlit UI**: Real-time interactive dashboard
- **Simplified Output**: Entity-confidence mapping format

## Architecture

```
┌─────────────────────────────────────────┐
│      Browser (http://localhost:8501)    │
│              Streamlit UI               │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
               ▼
┌─────────────────────────────────────────┐
│      FastAPI Backend (:8000)            │
│      - /analyze endpoint                │
│      - /health endpoint                 │
│      - /stats endpoint                  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Core Analysis Engine               │
│      - POCImpactAssessor                │
│      - SemanticImpactEngine             │
│      - EconomicKnowledgeGraph           │
└─────────────────────────────────────────┘
```

## New Files

```
ai-hl-processor/
├── models.py                 # Pydantic models for API
├── api_service.py            # FastAPI backend service
├── streamlit_app.py          # Streamlit UI dashboard
├── start_services.py         # Startup script
├── PHASE1_README.md          # This file
└── requirements.txt          # Updated with FastAPI + Streamlit
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `fastapi` - Web framework for API
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `streamlit` - UI framework
- `plotly` - Interactive charts
- `requests` - HTTP client

### 2. Configure Environment

Ensure your `.env` file is set up:

```bash
# For testing with mock LLM
ENV=test

# For production with Gemini Flash
ENV=prod
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
```

## Running the Application

### Option 1: One-Command Startup (Recommended)

```bash
python start_services.py
```

This will:
1. Check dependencies
2. Start FastAPI backend on port 8000
3. Start Streamlit UI on port 8501
4. Open browser automatically

### Option 2: Manual Startup

**Terminal 1 - Start API:**
```bash
python api_service.py
# or
uvicorn api_service:app --reload --port 8000
```

**Terminal 2 - Start UI:**
```bash
streamlit run streamlit_app.py
```

## Accessing the Application

- **Streamlit Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health
- **API Stats**: http://localhost:8000/stats

## Using the API

### Analyze Single Headline

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Rachel Reeves increased the tax",
    "min_confidence": 0.3
  }'
```

**Response:**
```json
{
  "headline": "Rachel Reeves increased the tax",
  "impacted_entities": [
    {
      "currency": "GBP",
      "confidence": "high",
      "confidence_score": 0.85,
      "reasoning": "UK Chancellor fiscal policy directly impacts British pound"
    },
    {
      "currency": "EUR",
      "confidence": "low",
      "confidence_score": 0.35,
      "reasoning": "Indirect impact via UK-EU trade relationship"
    }
  ],
  "processing_time_ms": 450,
  "analysis_timestamp": "2025-01-09T12:34:56.789Z",
  "metadata": {
    "total_entities_analyzed": 8,
    "entities_above_threshold": 2,
    "overall_confidence": 0.72
  }
}
```

### Batch Analysis

```bash
curl -X POST http://localhost:8000/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{
    "headlines": [
      "Fed raises interest rates",
      "ECB announces bond buying program",
      "OPEC cuts oil production"
    ],
    "min_confidence": 0.3
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0-phase1",
  "environment": "test",
  "model_provider": "mock_llm"
}
```

## Using the Streamlit UI

### 1. Analyze Headlines

1. Open http://localhost:8501
2. Enter a news headline in the text area
3. Click "🚀 Analyze Impact"
4. View results in:
   - **Cards View**: Detailed cards for each entity
   - **Chart View**: Visual confidence chart
   - **Table View**: Sortable table

### 2. Try Example Headlines

Click any example button:
- 📈 Fed raises interest rates
- 🇬🇧 UK tax increase
- ⚠️ Russia-Ukraine conflict
- 🛢️ OPEC production cuts

### 3. Adjust Settings

In the sidebar:
- **Minimum Confidence Threshold**: Filter entities by confidence
- **Auto-refresh**: Enable periodic updates
- **API Stats**: View performance statistics

### 4. Export Results

- **Download as JSON**: Full structured data
- **Download as CSV**: Tabular format for Excel

## Output Format (Phase 1)

### Simplified Entity-Confidence Mapping

```json
{
  "headline": "string",
  "impacted_entities": [
    {
      "currency": "string",           // e.g., "GBP", "EURUSD"
      "confidence": "high|medium|low", // Categorical
      "confidence_score": 0.0-1.0,     // Numeric
      "reasoning": "string"            // Explanation
    }
  ],
  "processing_time_ms": float,
  "analysis_timestamp": "ISO8601",
  "metadata": {}
}
```

### Confidence Levels

- **High** (>0.7): Strong impact expected, high reliability
- **Medium** (0.4-0.7): Moderate impact, some uncertainty
- **Low** (<0.4): Minor impact or high uncertainty

## API Endpoints

### POST /analyze

Analyze a single news headline.

**Request:**
```json
{
  "headline": "string",
  "target_entities": ["string"],  // Optional
  "min_confidence": float         // Optional, default 0.3
}
```

**Response:** `NewsAnalysisResponse`

### POST /analyze/batch

Analyze multiple headlines (max 100).

**Request:**
```json
{
  "headlines": ["string"],
  "min_confidence": float  // Optional, default 0.3
}
```

**Response:** `BatchAnalysisResponse`

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "string",
  "environment": "string",
  "model_provider": "string"
}
```

### GET /stats

Performance statistics.

**Response:**
```json
{
  "analyses_completed": int,
  "total_processing_time": float,
  "average_processing_time": float,
  "entities_processed": int
}
```

## Environment Configuration

### Test Environment (Default)
```ini
[test]
provider = mock_llm
use_mock_llm = true
max_concurrent_llm_calls = 1
log_level = WARNING
```

### Production Environment
```ini
[prod]
provider = gemini_flash
use_mock_llm = false
max_concurrent_llm_calls = 10
log_level = WARNING
```

## Troubleshooting

### API Won't Start

**Error**: `Address already in use`
```bash
# Find process using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
```

### Streamlit Won't Connect to API

1. Check API is running: `curl http://localhost:8000/health`
2. Check logs in FastAPI terminal
3. Verify CORS is enabled in `api_service.py`

### Missing Dependencies

```bash
pip install -r requirements.txt
```

### Google Cloud Authentication Issues

```bash
# Set credentials path
export GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Verify project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Test with dev/test environment first
ENV=test python start_services.py
```

## Development

### Adding New API Endpoints

1. Add route in `api_service.py`
2. Define request/response models in `models.py`
3. Update API documentation
4. Test with `/docs` interface

### Modifying UI

1. Edit `streamlit_app.py`
2. Streamlit auto-reloads on file changes
3. Refresh browser to see updates

### Testing

```bash
# Test API directly
curl http://localhost:8000/health

# Test with main.py CLI (still works)
python main.py demo

# Run component tests
python main.py test
```

## Migration from CLI

The original CLI (`main.py`) still works:

```bash
# Old way (still supported)
python main.py analyze "Fed raises rates"

# New way (API)
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"headline": "Fed raises rates"}'

# New way (UI)
# Open http://localhost:8501
```

## Next Steps

### Future Enhancements

1. **WebSocket Support**: Real-time streaming updates
2. **Redis Caching**: Cache analysis results
3. **Authentication**: API key/JWT authentication
4. **Rate Limiting**: Protect against abuse
5. **Monitoring**: Prometheus metrics, logging
6. **Database**: Store analysis history
7. **Kubernetes**: Deploy with HELM charts
8. **CI/CD**: Automated testing and deployment

### Phase 2 Considerations

- Historical analysis tracking
- User accounts and saved searches
- Custom entity definitions
- Webhook notifications
- Email alerts
- Advanced filtering and search

## Support

For issues or questions:
- Check logs in terminal
- Review API docs at `/docs`
- See main README.md for general setup
- Check CLAUDE.md for architecture details
