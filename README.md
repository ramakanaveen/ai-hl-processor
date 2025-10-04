# Financial News Impact Analysis System

A real-time semantic analysis system for assessing the impact of Bloomberg news headlines on financial markets, trading algorithms, and derivative pricing. The system uses advanced LLMs (Gemini Flash) combined with economic knowledge graphs to provide probabilistic impact assessments with <2 second response times.

## 🚀 Key Features

- **Semantic News Analysis**: Extract structured events and causal relationships from financial headlines
- **Multi-Dimensional Impact Assessment**: Analyze impact across currencies, algorithms, and derivatives
- **Economic Knowledge Graph**: Pre-built relationships between countries, currencies, and economic dependencies
- **Real-Time Processing**: Sub-2 second response times with parallel entity assessment
- **Causal Reasoning**: Understanding of second and third-order economic effects
- **Scalable Architecture**: Hybrid LLM + fine-tuned model approach for production scaling

## 📊 System Architecture

```
Bloomberg News Feed
        ↓
┌─────────────────────────────────────────────────────────┐
│                 News Ingestion                          │
│  • Semantic Event Extraction                           │
│  • Entity Relevance Filtering                          │
│  • Economic Context Enrichment                         │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│              Impact Propagation Engine                  │
│  • Economic Relationship Graph                         │
│  • Multi-Entity Assessment (Parallel)                  │
│  • Feature Engineering Pipeline                        │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│                Model Inference                          │
│  • Gemini Flash (POC)                                  │
│  • Fine-tuned BERT (Production)                        │
│  • Probability Distribution Output                     │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Use Cases

### Case 1: Currency Impact Analysis
- **Input**: "Russia launches missile attack on Ukrainian energy infrastructure"
- **Analysis**: Direct conflict impact → Energy supply disruption → Safe haven flows → EUR weakness
- **Output**:
  - EURUSD: Major Impact (0.65), Moderate (0.25), Minor (0.10)
  - USDJPY: Minor Impact (safe haven inflow)

### Case 2: Algorithm Impact Assessment
- **Input**: "Federal Reserve raises interest rates by 0.75 basis points"
- **Analysis**: Monetary policy change → Volatility regime shift → Algorithm performance impact
- **Output**: Momentum algos affected differently than mean-reversion strategies

### Case 3: Derivative Pricing Impact
- **Input**: "OPEC+ announces surprise oil production cut"
- **Analysis**: Supply shock → Commodity price spike → Volatility surface changes → Option pricing impact

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Google Cloud Project (for Vertex AI)
- Redis (for caching)
- PostgreSQL (optional, for historical data)

### Setup

1. **Clone and Install Dependencies**
```bash
git clone <repository-url>
cd financial-news-impact-analysis
pip install -r requirements.txt
```

2. **Environment Configuration**
```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export VERTEX_AI_API_KEY="your-api-key"
export ENVIRONMENT="development"  # or staging, production

# Optional: Database configuration
export DB_HOST="localhost"
export DB_USERNAME="finance_user"
export DB_PASSWORD="your-password"
```

3. **Initialize Configuration**
```python
from config import initialize_config, Environment

# Initialize for development
config = initialize_config(Environment.DEVELOPMENT)
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from poc_implementation import POCImpactAssessor

async def analyze_news():
    # Initialize the system
    assessor = POCImpactAssessor(use_mock_llm=True)

    # Analyze a news headline
    headline = "ECB announces emergency bond buying program"
    result = await assessor.analyze_news_impact(headline)

    # View results
    print(f"Processing Time: {result.total_processing_time_ms:.1f}ms")
    print(f"Entities Analyzed: {result.entities_processed}")

    for assessment in result.entity_assessments:
        print(f"\n{assessment.entity_id}:")
        print(f"  Major Impact: {assessment.probabilities.case_3_major:.3f}")
        print(f"  Reasoning: {assessment.reasoning}")

# Run the analysis
asyncio.run(analyze_news())
```

### Advanced Configuration

```python
# Configure for production with Gemini Flash
assessor = POCImpactAssessor(
    use_mock_llm=False,
    vertex_ai_project="your-project-id"
)

# Analyze specific entities
target_entities = ["EURUSD", "momentum_algo_1", "fx_option_eurusd"]
result = await assessor.analyze_news_impact(
    headline,
    target_entities=target_entities
)
```

## 📁 Project Structure

```
financial-news-impact-analysis/
├── semantic_impact_engine.py      # Core semantic analysis engine
├── economic_knowledge_graph.py    # Economic relationships and dependencies
├── feature_engineering.py         # Multi-dimensional feature extraction
├── poc_implementation.py          # POC with Gemini Flash integration
├── config.py                      # Configuration management
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── examples/
    ├── basic_usage.py             # Simple usage examples
    ├── batch_processing.py        # Batch analysis examples
    └── custom_entities.py         # Custom entity configuration
```

## 🔧 Configuration

The system supports multiple environments with different configurations:

### Development
- Mock LLM for testing
- Reduced concurrency limits
- Debug logging enabled
- No rate limiting

### Staging
- Gemini Flash integration
- Moderate concurrency
- Performance monitoring
- Security features enabled

### Production
- Full Gemini Flash deployment
- Maximum concurrency
- Comprehensive monitoring
- All security features

### Configuration Example

```python
from config import get_config, Environment

# Get production configuration
config = get_config(Environment.PRODUCTION)

# Access typed configuration objects
print(f"LLM Provider: {config.llm_config.provider}")
print(f"Max Concurrent Calls: {config.performance_config.max_concurrent_llm_calls}")
print(f"Cache TTL: {config.cache_config.cache_ttl_seconds}")
```

## 🎯 Performance Targets

| Metric | POC Target | Production Target |
|--------|------------|-------------------|
| Response Time (p95) | <2.0s | <1.0s |
| Throughput | 50 news/min | 200+ news/min |
| Accuracy | >75% | >85% |
| Entities per Analysis | 20 | 100+ |

## 🔄 Model Evolution Path

### Phase 1: POC (Current)
- **Model**: Gemini Flash via Vertex AI
- **Features**: Semantic analysis + economic context
- **Latency**: 1-2 seconds
- **Accuracy**: 75-80%

### Phase 2: Hybrid
- **Primary**: Fine-tuned FinBERT/DistilBERT
- **Fallback**: Gemini Flash for complex cases
- **Latency**: 200-500ms
- **Accuracy**: 80-85%

### Phase 3: Production
- **Primary**: Custom transformer optimized for financial news
- **Secondary**: Ensemble of specialized models
- **Latency**: 50-200ms
- **Accuracy**: 85-90%

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_semantic_engine.py
pytest tests/test_feature_engineering.py
pytest tests/test_poc_implementation.py

# Run with coverage
pytest --cov=. tests/
```

## 📈 Monitoring

The system includes comprehensive monitoring:

- **Prometheus metrics** for performance tracking
- **Structured logging** for debugging
- **Alert webhooks** for critical issues
- **Performance statistics** tracking

```python
# Get performance statistics
stats = assessor.get_performance_stats()
print(f"Average processing time: {stats['average_processing_time']:.2f}ms")
print(f"Entities processed: {stats['entities_processed']}")
```

## 🔒 Security

- **API key encryption** for sensitive credentials
- **Rate limiting** to prevent abuse
- **Request validation** for input sanitization
- **Audit logging** for compliance
- **JWT authentication** for API access

## 🚀 Deployment

### Docker Deployment
```bash
# Build container
docker build -t financial-news-analyzer .

# Run with environment variables
docker run -e GOOGLE_CLOUD_PROJECT=your-project \
           -e ENVIRONMENT=production \
           financial-news-analyzer
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: news-impact-analyzer
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: analyzer
        image: financial-news-analyzer:latest
        env:
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review example usage in `/examples`

## 🔮 Roadmap

- [ ] Bloomberg Terminal integration
- [ ] Real-time market data feeds
- [ ] Advanced sentiment analysis
- [ ] Model fine-tuning pipeline
- [ ] Historical backtesting framework
- [ ] Multi-language news support
- [ ] Custom algorithm integration
- [ ] Risk management features