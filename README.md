# AI Headline Impact Processor

A real-time semantic analysis system for assessing the impact of financial news headlines on markets, currencies, and trading algorithms. The system uses advanced LLMs (Google Gemini Flash) combined with economic knowledge graphs to provide probabilistic impact assessments with <2 second response times.

## 🚀 Key Features

- **Semantic News Analysis**: Extract structured events and causal relationships from financial headlines
- **Multi-Dimensional Impact Assessment**: Analyze impact across currencies, commodities, and trading algorithms
- **Economic Knowledge Graph**: Pre-built relationships between countries, currencies, and economic dependencies
- **Real-Time Processing**: Sub-2 second response times with parallel entity assessment
- **Causal Reasoning**: Understanding of second and third-order economic effects
- **Environment-Based Configuration**: Separate configs for test/dev/uat/prod environments
- **CLI & API Interface**: Full command-line tool and Python API

## 📊 System Architecture

```
Financial News Headline
        ↓
┌─────────────────────────────────────────────────────────┐
│              Semantic Impact Engine                     │
│  • Event Extraction (LLM-powered)                      │
│  • Entity Relevance Detection                          │
│  • Economic Context Enrichment                         │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│          Economic Knowledge Graph                       │
│  • Country-Currency Relationships                      │
│  • Trade Dependencies                                  │
│  • Economic Relationships                              │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│            Feature Engineering Pipeline                 │
│  • Contextual Feature Extraction                       │
│  • Entity-Specific Features                            │
│  • Multi-dimensional Feature Vectors                   │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│              Impact Assessment Engine                   │
│  • Google Gemini Flash (Production/UAT)                │
│  • Mock LLM (Test/Dev)                                 │
│  • Probability Distribution Output                     │
│  • Parallel Entity Processing                          │
└─────────────────────────────────────────────────────────┘
```

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Google Cloud Project with Vertex AI enabled (for production/UAT)
- Service account credentials

### Setup

1. **Clone and Install Dependencies**
```bash
git clone https://github.com/ramakanaveen/ai-hl-processor.git
cd ai-hl-processor
pip install -r requirements.txt
```

2. **Environment Configuration**

Copy the example environment file and configure it:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/service-account-key.json

# Environment (optional, defaults to 'test')
ENV=test  # Options: test, dev, uat, prod

# Database (optional)
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=finance_user
DB_PASSWORD=your-password
DB_NAME=financial_news_db

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 🚀 Quick Start

### Command Line Interface

The system provides a comprehensive CLI for all operations:

**Run Demo** (analyze sample headlines):
```bash
python main.py demo

# Analyze specific number of headlines
python main.py demo --count 3
```

**Analyze Single Headline**:
```bash
python main.py analyze "Fed raises interest rates by 0.75%"

# With specific entities
python main.py analyze "ECB bond buying program" --entities EURUSD GBPUSD

# Different output formats
python main.py analyze "Russia attacks Ukraine" --format json
python main.py analyze "OPEC cuts production" --format table

# Save to file
python main.py analyze "BOE intervenes" --output results.json
```

**Batch Processing**:
```bash
# Process multiple headlines from file
python main.py batch --input headlines.txt --output results.json

# Control concurrency
python main.py batch --input headlines.txt --output results.json --max-concurrent 10
```

**Test System Components**:
```bash
# Test all components
python main.py test

# Test specific component
python main.py test --component semantic
python main.py test --component economic
python main.py test --component poc
```

**Performance Benchmark**:
```bash
python main.py benchmark --iterations 20
```

**Environment Control**:
```bash
# Use specific environment via CLI
python main.py demo --environment prod

# Use environment via ENV variable
ENV=uat python main.py demo

# Enable verbose logging
python main.py demo --verbose
```

### Python API Usage

```python
import asyncio
from poc_implementation import POCImpactAssessor

async def analyze_news():
    # Initialize the assessor
    assessor = POCImpactAssessor()

    # Analyze a news headline
    headline = "ECB announces emergency bond buying program"
    result = await assessor.analyze_news_impact(headline)

    # View results
    print(f"Processing Time: {result.total_processing_time_ms:.1f}ms")
    print(f"Entities Analyzed: {result.entities_processed}")
    print(f"Overall Confidence: {result.overall_confidence:.3f}")

    # View entity assessments
    for assessment in result.entity_assessments:
        print(f"\n{assessment.entity_id}:")
        print(f"  Major Impact: {assessment.probabilities.case_3_major:.3f}")
        print(f"  Moderate Impact: {assessment.probabilities.case_2_moderate:.3f}")
        print(f"  Minor Impact: {assessment.probabilities.case_1_minor:.3f}")
        print(f"  Confidence: {assessment.confidence_score:.3f}")

# Run the analysis
asyncio.run(analyze_news())
```

**Advanced Configuration**:
```python
from config_loader import get_config

# Load specific environment configuration
config = get_config(environment='prod')

# Access configuration
print(f"Model: {config.model_config.model_name}")
print(f"Provider: {config.model_config.provider}")
print(f"Using Mock LLM: {config.model_config.use_mock_llm}")
print(f"Max Concurrent Calls: {config.performance_config.max_concurrent_llm_calls}")

# Validate configuration
issues = config.validate_config()
if issues:
    for issue in issues:
        print(f"Warning: {issue}")
```

## 📁 Project Structure

```
ai-hl-processor/
├── main.py                        # CLI entry point with full command interface
├── config_loader.py               # Environment-based configuration system
├── config.ini                     # Configuration file (test/dev/uat/prod)
├── semantic_impact_engine.py      # Core semantic analysis engine
├── economic_knowledge_graph.py    # Economic relationships and dependencies
├── feature_engineering.py         # Multi-dimensional feature extraction
├── poc_implementation.py          # POC with Google Gemini integration
├── requirements.txt               # Python dependencies
├── requirements-minimal.txt       # Minimal dependencies for testing
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## 🔧 Configuration

### Environment Types

The system uses `config.ini` with four environment sections:

#### `[test]` - Test Environment
- Mock LLM for fast testing
- Minimal concurrency (1 concurrent call)
- Short timeouts (10s)
- Warning-level logging
- No monitoring/metrics

#### `[dev]` - Development Environment
- Mock LLM for development
- Low concurrency (2 concurrent calls)
- Debug logging enabled
- Feature caching disabled
- No rate limiting

#### `[uat]` - UAT Environment
- Real Google Gemini Flash
- Moderate concurrency (3 concurrent calls)
- Info-level logging
- Prometheus metrics enabled
- Audit logging enabled

#### `[prod]` - Production Environment
- Real Google Gemini Flash
- High concurrency (10 concurrent calls)
- Warning-level logging
- All security features enabled
- Rate limiting enabled
- Request validation enabled
- Full monitoring stack

### Configuration Priority

The environment is determined in this order:
1. CLI argument: `--environment prod`
2. ENV variable: `ENV=uat`
3. Default: `test`

### Configuration File Structure

```ini
[DEFAULT]
# Shared defaults for all environments
max_tokens = 2048
temperature = 0.3
timeout_seconds = 30
...

[test]
# Test-specific overrides
provider = mock_llm
use_mock_llm = true
log_level = WARNING
...

[prod]
# Production-specific overrides
provider = gemini_flash
use_mock_llm = false
rate_limit_rpm = 300
log_level = WARNING
...
```

## 🎯 Example Use Cases

### Case 1: Currency Impact Analysis
**Input**: "Russia launches missile attack on Ukrainian energy infrastructure"

**Analysis Chain**:
- Direct conflict impact detected
- Energy supply disruption inferred
- Safe haven flow prediction
- EUR weakness expected

**Output**:
```
EURUSD:
  Major Impact: 0.650
  Moderate Impact: 0.250
  Minor Impact: 0.100
  Confidence: 0.85
```

### Case 2: Central Bank Policy
**Input**: "Federal Reserve raises interest rates by 0.75 basis points"

**Analysis Chain**:
- Monetary policy tightening
- USD strengthening expected
- Cross-currency impacts analyzed

**Output**:
```
EURUSD: Major Impact (USD strength)
USDJPY: Moderate Impact (rate differential)
GBPUSD: Major Impact (USD strength)
```

### Case 3: Commodity Shock
**Input**: "OPEC+ announces surprise oil production cut of 2 million barrels per day"

**Analysis Chain**:
- Supply shock identified
- Oil price surge expected
- Energy exporter currencies strengthened
- Commodity-linked impacts

## 🎯 Performance Targets

| Metric | Test/Dev | UAT | Production |
|--------|----------|-----|------------|
| Response Time (p95) | N/A | <2.0s | <1.5s |
| Concurrent Calls | 1-2 | 3 | 10 |
| Mock LLM | Yes | No | No |
| Rate Limiting | No | Yes | Yes |
| Monitoring | No | Yes | Yes |

## 📈 Monitoring & Statistics

Get runtime statistics:
```python
stats = assessor.get_performance_stats()
print(f"Analyses completed: {stats['analyses_completed']}")
print(f"Average time: {stats['average_processing_time']:.2f}ms")
print(f"Entities processed: {stats['entities_processed']}")
```

## 🧪 Testing

**Run all system tests**:
```bash
python main.py test
```

**Test specific components**:
```bash
python main.py test --component semantic    # Semantic engine
python main.py test --component economic    # Knowledge graph
python main.py test --component features    # Feature engineering
python main.py test --component poc         # POC implementation
```

**Run benchmarks**:
```bash
python main.py benchmark --iterations 50
```

## 🔒 Security Features

- **Environment isolation**: Separate configs for each environment
- **Credential management**: Google Cloud credentials via service account
- **Input validation**: Request validation in production
- **Rate limiting**: Configurable rate limits per environment
- **Audit logging**: Full audit trail in UAT/production
- **.env protection**: Credentials never committed to git

## 🚀 Deployment Checklist

### Development
```bash
ENV=dev python main.py demo
```

### UAT
1. Set `ENV=uat` or use `--environment uat`
2. Ensure `GOOGLE_CLOUD_PROJECT` is set
3. Ensure `GOOGLE_CREDENTIALS_PATH` points to valid service account
4. Run: `python main.py test` to verify setup

### Production
1. Set `ENV=prod` or use `--environment prod`
2. Verify Google Cloud credentials
3. Test configuration: `python main.py test --component all`
4. Run benchmark: `python main.py benchmark`
5. Monitor metrics and logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes (`python main.py test`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues or questions:
- Create an issue on GitHub
- Check the configuration documentation in `config.ini`
- Review CLI help: `python main.py --help`

## 🔮 Roadmap

- [ ] Bloomberg Terminal integration
- [ ] Real-time streaming mode
- [ ] Historical backtesting framework
- [ ] Fine-tuned model for production (replace Gemini)
- [ ] Multi-language support
- [ ] Advanced caching layer with Redis
- [ ] API server with FastAPI
- [ ] Web dashboard for monitoring
- [ ] Custom entity definitions
- [ ] Webhook notification support
