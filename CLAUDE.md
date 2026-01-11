# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered financial news headline impact analyzer that uses semantic analysis and economic knowledge graphs to assess the probability of market impact across currencies, commodities, and trading algorithms. Achieves sub-2 second response times using Google Gemini Flash (production) or mock LLM (test/dev).

## Core Architecture

### Pipeline Flow

```
News Headline → Semantic Analysis → Economic Context → Feature Engineering → Impact Assessment → Probability Distribution
```

**Key Processing Path:**
1. **Entity Relevance Filtering** (EntityRelevanceFilter in poc_implementation.py:350-396) - Fast keyword-based filtering to identify relevant trading entities (EURUSD, GBPUSD, etc.)
2. **Semantic Event Extraction** (SemanticImpactEngine in semantic_impact_engine.py:304-404) - Extracts event type, severity, affected sectors, and time horizon
3. **Economic Context Enrichment** (EconomicKnowledgeBase in economic_knowledge_graph.py:57-350) - Adds trade relationships, currency dependencies, commodity exposure
4. **Feature Engineering** (ContextualFeatureBuilder in feature_engineering.py) - Multi-dimensional feature vectors (semantic, economic, sentiment, technical)
5. **Parallel Impact Assessment** (POCImpactAssessor in poc_implementation.py:398-673) - Concurrent LLM calls (configurable via max_concurrent_llm_calls) to assess each entity
6. **Probability Generation** - Returns probability distribution across 4 cases: abstain, minor (<2%), moderate (2-5%), major (>5%)

### Key Components

**poc_implementation.py** - Main orchestration layer
- POCImpactAssessor: Entry point for analysis
- VertexAIClient: Google Gemini Flash integration (lines 127-348)
- MockLLMClient: Test/dev mock with realistic response templates (lines 54-125)
- Handles concurrency via asyncio.Semaphore (lines 467-470)

**semantic_impact_engine.py** - Event extraction and classification
- SemanticNewsAnalyzer: Extracts structured events (EventType, SeverityLevel, TimeHorizon)
- ImpactPropagationEngine: Propagates impact through economic graph
- Falls back to rule-based extraction if LLM unavailable

**economic_knowledge_graph.py** - Static economic relationships
- Trade relationships between countries (e.g., USA-China: 0.18 trade weight)
- Supply chain dependencies (semiconductors, energy, agriculture)
- Currency correlations and safe haven flows
- Economic indicators (GDP, trade openness, debt ratios)

**feature_engineering.py** - Feature vector generation
- NewsSemanticFeatureExtractor: Sentiment, urgency, sector keywords
- Multiple feature categories: semantic, economic context, market data, sentiment
- FeatureVector.to_array() for model input

**config_loader.py** - Environment-based configuration
- ConfigLoader handles test/dev/uat/prod environments
- Uses config.ini with environment-specific overrides
- Validates Google Cloud credentials when use_mock_llm=false

## Environment Management

The system uses a 4-tier environment strategy (config.ini):

**test** - Fast testing with mock LLM
- use_mock_llm=true, max_concurrent_llm_calls=1, timeout=10s

**dev** - Development with mock LLM
- use_mock_llm=true, max_concurrent_llm_calls=2, debug logging

**uat** - Real Gemini Flash, moderate scale
- use_mock_llm=false, max_concurrent_llm_calls=3, audit logging enabled

**prod** - Full-scale production
- use_mock_llm=false, max_concurrent_llm_calls=10, rate limiting, request validation

**Environment Selection Priority:**
1. CLI flag: `--environment prod`
2. ENV variable: `ENV=uat`
3. Default: `test`

## Common Commands

### Running Analysis

```bash
# Demo with sample headlines
python main.py demo

# Analyze single headline
python main.py analyze "Fed raises interest rates by 0.75%"

# With specific entities
python main.py analyze "ECB bond buying program" --entities EURUSD GBPUSD

# Different output formats (json, table, summary)
python main.py analyze "Russia attacks Ukraine" --format json

# Save to file
python main.py analyze "BOE intervenes" --output results.json
```

### Batch Processing

```bash
# Process multiple headlines from file
python main.py batch --input headlines.txt --output results.json

# Control concurrency
python main.py batch --input headlines.txt --output results.json --max-concurrent 10
```

### Testing

```bash
# Test all components
python main.py test

# Test specific component
python main.py test --component semantic   # Semantic engine
python main.py test --component economic   # Knowledge graph
python main.py test --component poc        # POC implementation
```

### Performance Benchmarking

```bash
python main.py benchmark --iterations 20
```

### Environment Control

```bash
# Use specific environment
python main.py demo --environment prod

# Via environment variable
ENV=uat python main.py demo

# Enable verbose logging
python main.py demo --verbose
```

## Configuration Notes

### Google Cloud Setup (UAT/Production)

Required environment variables in .env:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account-key.json
ENV=uat  # or prod
```

The VertexAIClient (poc_implementation.py:127-348) handles:
- Credential setup from GOOGLE_CREDENTIALS_PATH or GOOGLE_APPLICATION_CREDENTIALS
- Vertex AI initialization with project and region
- Prompt construction with economic context
- Response parsing (JSON extraction with fallback)

### Mock LLM vs Real LLM

**MockLLMClient** (poc_implementation.py:54-125) is used when use_mock_llm=true:
- Classifies news into conflict/monetary_policy/trade/default
- Returns predefined probability templates
- Simulates 0.1s API delay
- Entity-specific adjustments (safe haven currencies benefit from risk-off)

**VertexAIClient** switches to Gemini Flash when use_mock_llm=false:
- Calls GenerativeModel with structured prompt
- Temperature=0.3, max_tokens=2048 (from config)
- Fallback to MockLLMClient on import/API errors

## Development Patterns

### Adding New Entities

1. Add keyword mappings to EntityRelevanceFilter._build_entity_keyword_mapping() (poc_implementation.py:357-368)
2. Add entity context to EconomicKnowledgeBase.get_entity_context()
3. Update entity type mapping in POCImpactAssessor._determine_entity_type() (poc_implementation.py:578-591)

### Adding New Event Types

1. Extend EventType enum in semantic_impact_engine.py:20-28
2. Add classification keywords to SemanticNewsAnalyzer._load_event_patterns() (semantic_impact_engine.py:78-97)
3. Update LLM prompts in VertexAIClient._build_analysis_prompt() (poc_implementation.py:216-264)

### Modifying Impact Assessment Logic

The core probability calculation happens in:
- MockLLMClient.analyze_impact() for test/dev (poc_implementation.py:83-111)
- VertexAIClient.analyze_semantic_impact() for uat/prod (poc_implementation.py:155-214)
- Probabilities must sum to 1.0 (normalized in _parse_gemini_response, line 301-304)

### Concurrency Control

Parallel entity assessment uses asyncio.Semaphore:
```python
semaphore = asyncio.Semaphore(config.performance_config.max_concurrent_llm_calls)
results = await asyncio.gather(*[self._semaphore_wrapper(semaphore, task) for task in tasks])
```
Adjust max_concurrent_llm_calls in config.ini to control parallelism.

## Important Implementation Details

### Probability Distribution Format

All assessments return ImpactProbabilities with 4 cases:
- **abstain**: No significant impact or unclear (0-1)
- **case_1_minor**: <2% market movement (0-1)
- **case_2_moderate**: 2-5% impact (0-1)
- **case_3_major**: >5% impact (0-1)

Must sum to 1.0. See semantic_impact_engine.py:61-69 for dataclass.

### Response Time Optimization

Target: <2 second p95 response time (prod)

Achieved via:
1. Fast entity filtering (keyword matching, not LLM)
2. Parallel LLM calls with semaphore
3. Feature caching (if enabled in config)
4. Gemini Flash (fast model, not full Gemini Pro)

Monitor via get_performance_stats() which tracks analyses_completed, average_processing_time, entities_processed.

### Error Handling Strategy

- LLM failures fall back to MockLLMClient (see poc_implementation.py:204-214)
- JSON parsing failures use _fallback_response_parsing() (poc_implementation.py:321-347)
- Entity assessment failures are caught and filtered out (poc_implementation.py:473-477)
- Empty results handled via _create_empty_result() (poc_implementation.py:593-604)

### Economic Knowledge Graph Structure

Pre-loaded static data includes:
- Trade relationships: Dict[country, Dict[partner, weight]]
- Supply chain dependencies by sector (semiconductors, energy, agriculture)
- Currency correlations: Dict[currency_pair, correlation_coefficient]
- Safe haven hierarchies (CHF > JPY > USD > Gold)

See EconomicKnowledgeBase._initialize_*() methods for data.

## Testing Strategy

Component tests (main.py:273-296):
- **semantic**: Tests SemanticImpactEngine event extraction
- **economic**: Tests EconomicKnowledgeBase context retrieval and relationship graph
- **features**: Tests ContextualFeatureBuilder feature generation
- **poc**: Tests end-to-end POCImpactAssessor analysis

All tests use async/await. Run with `python main.py test --component all`.

## Output Formats

**Summary** (default): Top 5 entities with major/moderate/minor probabilities
**JSON**: Full structured output with all assessments
**Table**: Tabular format with all probability columns

Export to JSON via:
```python
filename = assessor.export_results_to_json(result, "output.json")
```

Results include metadata: relevant_entities_found, successful_assessments, failed_assessments, average_entity_processing_time.