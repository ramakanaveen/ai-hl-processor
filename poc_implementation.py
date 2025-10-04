"""
POC Implementation for Financial News Impact Analysis
Gemini Flash-based semantic analysis with hybrid architecture support
"""

import asyncio
import logging
import json
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our custom modules
from semantic_impact_engine import SemanticImpactEngine, ImpactProbabilities
from economic_knowledge_graph import EconomicKnowledgeBase, EconomicRelationshipGraph
from feature_engineering import ContextualFeatureBuilder, EntityType, FeatureVector
from config_loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class ImpactAssessmentResult:
    """Results from impact assessment for a single entity"""
    entity_id: str
    entity_type: str
    probabilities: ImpactProbabilities
    feature_vector: FeatureVector
    processing_time_ms: float
    confidence_score: float
    reasoning: str


@dataclass
class NewsAnalysisResult:
    """Complete analysis results for a news headline"""
    news_headline: str
    analysis_timestamp: datetime
    semantic_event: Optional[Any]
    entity_assessments: List[ImpactAssessmentResult]
    total_processing_time_ms: float
    entities_processed: int
    overall_confidence: float
    metadata: Dict[str, Any]


class MockLLMClient:
    """Mock LLM client for testing - replace with actual Gemini Flash implementation"""

    def __init__(self):
        config = get_config()
        self.model_name = config.model_config.model_name
        self.response_templates = self._load_response_templates()

    def _load_response_templates(self) -> Dict[str, Any]:
        """Load mock response templates for different news types"""
        return {
            'conflict': {
                'probabilities': {'abstain': 0.1, 'case_1_minor': 0.2, 'case_2_moderate': 0.4, 'case_3_major': 0.3},
                'reasoning': 'Military conflict creates significant market uncertainty and risk-off sentiment'
            },
            'monetary_policy': {
                'probabilities': {'abstain': 0.15, 'case_1_minor': 0.35, 'case_2_moderate': 0.35, 'case_3_major': 0.15},
                'reasoning': 'Central bank actions have moderate impact on currency and interest rate sensitive assets'
            },
            'trade': {
                'probabilities': {'abstain': 0.2, 'case_1_minor': 0.3, 'case_2_moderate': 0.3, 'case_3_major': 0.2},
                'reasoning': 'Trade policy changes affect bilateral relationships and specific sectors'
            },
            'default': {
                'probabilities': {'abstain': 0.3, 'case_1_minor': 0.4, 'case_2_moderate': 0.2, 'case_3_major': 0.1},
                'reasoning': 'General market impact with moderate uncertainty'
            }
        }

    async def analyze_impact(self, news_headline: str, entity_id: str,
                           entity_context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock LLM analysis - replace with actual Gemini Flash API call"""

        # Simulate API call delay
        await asyncio.sleep(0.1)

        # Determine news type for appropriate template
        news_type = self._classify_news_type(news_headline)
        template = self.response_templates.get(news_type, self.response_templates['default'])

        # Add some entity-specific variation
        probabilities = template['probabilities'].copy()
        if 'safe_haven' in entity_context.get('currency_group', []):
            # Safe haven currencies benefit from risk-off events
            if news_type == 'conflict':
                probabilities['case_3_major'] += 0.1
                probabilities['abstain'] -= 0.1

        # Normalize probabilities
        total = sum(probabilities.values())
        probabilities = {k: v/total for k, v in probabilities.items()}

        return {
            'probabilities': probabilities,
            'reasoning': template['reasoning'] + f" (Entity: {entity_id})",
            'confidence': 0.8,
            'model_used': self.model_name
        }

    def _classify_news_type(self, news_headline: str) -> str:
        """Classify news type based on keywords"""
        headline_lower = news_headline.lower()

        if any(word in headline_lower for word in ['attack', 'war', 'conflict', 'missile', 'invasion']):
            return 'conflict'
        elif any(word in headline_lower for word in ['fed', 'ecb', 'interest rate', 'monetary policy']):
            return 'monetary_policy'
        elif any(word in headline_lower for word in ['trade', 'tariff', 'export', 'import']):
            return 'trade'
        else:
            return 'default'


class VertexAIClient:
    """Vertex AI client for Gemini Flash - implement actual API integration"""

    def __init__(self, project_id: str = None, region: str = None):
        config = get_config()
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region or config.model_config.google_cloud_region
        self.model_name = config.model_config.model_name

        # Set up Google credentials
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup Google Cloud credentials from environment variables"""
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

        if credentials_path:
            # Set the credentials path for Google Cloud SDK
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.info(f"Using Google credentials from: {credentials_path}")
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            logger.info("Using existing GOOGLE_APPLICATION_CREDENTIALS")
        else:
            logger.warning("No Google credentials found. Set GOOGLE_CREDENTIALS_PATH or GOOGLE_APPLICATION_CREDENTIALS")

        if not self.project_id:
            raise ValueError("Google Cloud project ID must be provided via GOOGLE_CLOUD_PROJECT environment variable or constructor parameter")

    async def analyze_semantic_impact(self, news_headline: str, entity_id: str,
                                    entity_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actual Gemini Flash implementation for semantic impact analysis
        """
        try:
            # Import Google Cloud AI Platform
            from google.cloud import aiplatform
            import json

            # Initialize AI Platform if not already done
            if not hasattr(self, '_client_initialized'):
                aiplatform.init(project=self.project_id, location=self.region)
                self._client_initialized = True

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(news_headline, entity_id, entity_context)

            # Use the new Gemini API approach
            import vertexai
            from vertexai.generative_models import GenerativeModel

            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.region)

            # Create the model
            model = GenerativeModel(self.model_name)

            # Configure generation parameters
            config = get_config()
            generation_config = {
                "temperature": config.model_config.temperature,
                "max_output_tokens": config.model_config.max_tokens,
                "top_p": 0.8,
                "top_k": 40
            }

            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Parse the response
            if response.text:
                return self._parse_gemini_response(response.text)
            else:
                raise Exception("No response text returned from Gemini")

        except ImportError:
            logger.warning("Google Cloud AI Platform not installed. Install with: pip install google-cloud-aiplatform")
            # Fall back to mock client
            mock_client = MockLLMClient()
            return await mock_client.analyze_impact(news_headline, entity_id, entity_context)

        except Exception as e:
            logger.error(f"Error calling Gemini Flash: {e}")
            # Fall back to mock client
            mock_client = MockLLMClient()
            return await mock_client.analyze_impact(news_headline, entity_id, entity_context)

    def _build_analysis_prompt(self, news_headline: str, entity_id: str,
                             entity_context: Dict[str, Any]) -> str:
        """Build structured prompt for Gemini Flash"""

        return f"""
        Analyze the financial impact of this news headline on the specified entity:

        NEWS: "{news_headline}"
        ENTITY: {entity_id}

        ENTITY CONTEXT:
        - Trade Partners: {entity_context.get('trade_partners', {})}
        - Economic Indicators: {entity_context.get('economic_indicators', {})}
        - Currency Groups: {entity_context.get('currency_group', [])}
        - Supply Chain Role: {entity_context.get('supply_chain_role', {})}

        ANALYSIS FRAMEWORK:
        1. Identify the core economic event and its implications
        2. Analyze transmission mechanisms to this entity:
           - Direct exposure (mentions, geography, sector)
           - Trade relationship impacts
           - Supply chain disruptions
           - Currency/financial flow effects
           - Sentiment and risk-off impacts
        3. Consider entity-specific factors:
           - Economic stability and vulnerability
           - Safe haven characteristics
           - Commodity dependencies
           - Geopolitical relationships

        REQUIRED OUTPUT (JSON format):
        {{
            "probabilities": {{
                "abstain": [0-1],  // No significant impact or unclear
                "case_1_minor": [0-1],  // Small market movement (<2%)
                "case_2_moderate": [0-1],  // Medium impact (2-5%)
                "case_3_major": [0-1]   // Large impact (>5%)
            }},
            "reasoning": "Detailed explanation of impact assessment and key transmission mechanisms",
            "confidence": [0-1],  // Confidence in this assessment
            "key_factors": ["factor1", "factor2", "factor3"],  // Main impact drivers
            "time_horizon": "immediate|short_term|medium_term",  // Expected impact timing
            "risk_factors": ["risk1", "risk2"]  // Key risks that could change assessment
        }}

        Focus on economic fundamentals and logical cause-effect relationships.
        Consider both positive and negative potential impacts.
        Be specific about WHY this entity would be affected.
        """

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini Flash response into structured format"""
        try:
            # Try to extract JSON from the response
            import re
            import json

            # Look for JSON-like content in the response - try multiple patterns
            json_match = None

            # Try to find JSON in code blocks first
            code_block_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if code_block_match:
                json_match = code_block_match
                json_str = code_block_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'{.*}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)

            if json_match:
                parsed_response = json.loads(json_str)

                # Validate the required fields
                if 'probabilities' in parsed_response:
                    probs = parsed_response['probabilities']

                    # Ensure all probability fields exist and sum to 1
                    required_fields = ['abstain', 'case_1_minor', 'case_2_moderate', 'case_3_major']
                    for field in required_fields:
                        if field not in probs:
                            probs[field] = 0.0

                    # Normalize probabilities to sum to 1
                    total = sum(probs.values())
                    if total > 0:
                        for field in required_fields:
                            probs[field] = probs[field] / total

                    return {
                        'probabilities': probs,
                        'reasoning': parsed_response.get('reasoning', 'Impact analysis completed'),
                        'confidence': parsed_response.get('confidence', 0.7),
                        'model_used': self.model_name
                    }

            # If JSON parsing fails, fall back to text analysis
            logger.warning("Could not parse JSON from Gemini response, using fallback parsing")
            return self._fallback_response_parsing(response_text)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parsing Gemini response: {e}, using fallback")
            return self._fallback_response_parsing(response_text)

    def _fallback_response_parsing(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing for non-JSON responses"""
        # Simple keyword-based analysis of the response
        text_lower = response_text.lower()

        # Default moderate impact
        probabilities = {
            'abstain': 0.2,
            'case_1_minor': 0.3,
            'case_2_moderate': 0.3,
            'case_3_major': 0.2
        }

        # Adjust based on keywords in response
        if any(word in text_lower for word in ['major', 'significant', 'severe', 'critical']):
            probabilities = {'abstain': 0.1, 'case_1_minor': 0.2, 'case_2_moderate': 0.3, 'case_3_major': 0.4}
        elif any(word in text_lower for word in ['minor', 'small', 'limited', 'slight']):
            probabilities = {'abstain': 0.15, 'case_1_minor': 0.5, 'case_2_moderate': 0.25, 'case_3_major': 0.1}
        elif any(word in text_lower for word in ['no impact', 'unclear', 'uncertain']):
            probabilities = {'abstain': 0.6, 'case_1_minor': 0.25, 'case_2_moderate': 0.1, 'case_3_major': 0.05}

        return {
            'probabilities': probabilities,
            'reasoning': f"Fallback analysis of response: {response_text[:200]}...",
            'confidence': 0.5,
            'model_used': f"{self.model_name}_fallback"
        }


class EntityRelevanceFilter:
    """Fast filtering to identify relevant entities for analysis"""

    def __init__(self, knowledge_base: EconomicKnowledgeBase):
        self.knowledge_base = knowledge_base
        self.entity_keywords = self._build_entity_keyword_mapping()

    def _build_entity_keyword_mapping(self) -> Dict[str, List[str]]:
        """Build keyword mappings for entity relevance"""
        return {
            'EURUSD': ['ECB', 'Federal Reserve', 'Fed', 'EUR', 'USD', 'Germany', 'USA', 'Europe'],
            'GBPUSD': ['BOE', 'Bank of England', 'Brexit', 'UK', 'Britain', 'pound', 'GBP'],
            'USDJPY': ['BOJ', 'Bank of Japan', 'yen', 'JPY', 'Japan', 'Tokyo'],
            'AUDUSD': ['RBA', 'Australia', 'commodity', 'iron ore', 'coal', 'AUD'],
            'USDCAD': ['BOC', 'Canada', 'oil', 'crude', 'CAD', 'NAFTA'],
            'XAUUSD': ['gold', 'precious metals', 'safe haven', 'inflation'],
            'WTI': ['oil', 'crude', 'energy', 'OPEC', 'petroleum', 'Russia', 'Saudi Arabia'],
            'BTC': ['bitcoin', 'crypto', 'digital currency', 'blockchain']
        }

    def get_relevant_entities(self, news_headline: str,
                            max_entities: int = 20) -> List[Tuple[str, float]]:
        """Get relevant entities with relevance scores"""

        headline_lower = news_headline.lower()
        entity_scores = []

        for entity, keywords in self.entity_keywords.items():
            score = 0.0

            # Keyword matching
            for keyword in keywords:
                if keyword.lower() in headline_lower:
                    score += 1.0

            # Boost score for exact matches
            if any(keyword.lower() == word for word in headline_lower.split()
                  for keyword in keywords):
                score += 0.5

            if score > 0:
                entity_scores.append((entity, score))

        # Sort by relevance and limit
        entity_scores.sort(key=lambda x: x[1], reverse=True)
        return entity_scores[:max_entities]


class POCImpactAssessor:
    """Main POC implementation for financial news impact analysis"""

    def __init__(self, use_mock_llm: bool = None, vertex_ai_project: str = None):
        # Initialize configuration
        config = get_config()

        # Use configuration to determine mock LLM usage if not explicitly specified
        if use_mock_llm is None:
            use_mock_llm = config.model_config.use_mock_llm

        # Initialize components
        self.knowledge_base = EconomicKnowledgeBase()
        self.economic_graph = EconomicRelationshipGraph(self.knowledge_base)
        self.feature_builder = ContextualFeatureBuilder(self.knowledge_base)
        self.entity_filter = EntityRelevanceFilter(self.knowledge_base)

        # Initialize LLM client
        if use_mock_llm:
            self.llm_client = MockLLMClient()
        else:
            self.llm_client = VertexAIClient(project_id=vertex_ai_project)

        # Initialize semantic engine
        self.semantic_engine = SemanticImpactEngine(
            llm_client=self.llm_client,
            economic_graph=self.economic_graph
        )

        # Performance tracking
        self.stats = {
            'analyses_completed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'entities_processed': 0
        }

    async def analyze_news_impact(self, news_headline: str,
                                target_entities: Optional[List[str]] = None) -> NewsAnalysisResult:
        """Complete news impact analysis"""

        start_time = time.time()

        try:
            # Step 1: Entity relevance filtering
            if target_entities:
                relevant_entities = [(entity, 1.0) for entity in target_entities]
            else:
                relevant_entities = self.entity_filter.get_relevant_entities(news_headline)

            if not relevant_entities:
                logger.warning("No relevant entities found for news headline")
                return self._create_empty_result(news_headline, start_time)

            logger.info(f"Analyzing {len(relevant_entities)} relevant entities")

            # Step 2: Semantic event extraction
            semantic_event = await self.semantic_engine.semantic_analyzer.extract_events(news_headline)

            # Step 3: Parallel entity assessment
            assessment_tasks = []
            for entity_id, relevance_score in relevant_entities:
                task = self._assess_entity_impact(
                    news_headline, entity_id, semantic_event, relevance_score
                )
                assessment_tasks.append(task)

            # Execute assessments in parallel (with concurrency limit)
            config = get_config()
            semaphore = asyncio.Semaphore(config.performance_config.max_concurrent_llm_calls)
            assessment_results = await asyncio.gather(
                *[self._semaphore_wrapper(semaphore, task) for task in assessment_tasks],
                return_exceptions=True
            )

            # Filter successful results
            successful_results = [
                result for result in assessment_results
                if isinstance(result, ImpactAssessmentResult)
            ]

            # Calculate overall metrics
            total_time_ms = (time.time() - start_time) * 1000
            overall_confidence = np.mean([r.confidence_score for r in successful_results]) if successful_results else 0.0

            # Update stats
            self._update_stats(total_time_ms, len(successful_results))

            # Create result
            result = NewsAnalysisResult(
                news_headline=news_headline,
                analysis_timestamp=datetime.now(),
                semantic_event=semantic_event,
                entity_assessments=successful_results,
                total_processing_time_ms=total_time_ms,
                entities_processed=len(successful_results),
                overall_confidence=overall_confidence,
                metadata={
                    'relevant_entities_found': len(relevant_entities),
                    'successful_assessments': len(successful_results),
                    'failed_assessments': len(assessment_results) - len(successful_results),
                    'average_entity_processing_time': np.mean([r.processing_time_ms for r in successful_results]) if successful_results else 0.0
                }
            )

            logger.info(f"Analysis completed in {total_time_ms:.1f}ms for {len(successful_results)} entities")
            return result

        except Exception as e:
            logger.error(f"Error in news impact analysis: {e}")
            return self._create_error_result(news_headline, start_time, str(e))

    async def _semaphore_wrapper(self, semaphore: asyncio.Semaphore, coro):
        """Wrapper to limit concurrent operations"""
        async with semaphore:
            return await coro

    async def _assess_entity_impact(self, news_headline: str, entity_id: str,
                                  semantic_event, relevance_score: float) -> ImpactAssessmentResult:
        """Assess impact for a single entity"""

        entity_start_time = time.time()

        try:
            # Determine entity type (simplified mapping)
            entity_type = self._determine_entity_type(entity_id)

            # Get entity context
            entity_context = self.knowledge_base.get_entity_context(entity_id)

            # Build features
            feature_vector = self.feature_builder.build_features(
                news_headline, entity_id, entity_type, semantic_event
            )

            # LLM-based impact assessment
            if hasattr(self.llm_client, 'analyze_impact'):
                # For MockLLMClient
                llm_result = await self.llm_client.analyze_impact(
                    news_headline, entity_id, entity_context
                )
            else:
                # For VertexAIClient
                llm_result = await self.llm_client.analyze_semantic_impact(
                    news_headline, entity_id, entity_context
                )

            # Create impact probabilities
            probabilities = ImpactProbabilities(
                abstain=llm_result['probabilities']['abstain'],
                case_1_minor=llm_result['probabilities']['case_1_minor'],
                case_2_moderate=llm_result['probabilities']['case_2_moderate'],
                case_3_major=llm_result['probabilities']['case_3_major'],
                reasoning=llm_result['reasoning'],
                confidence=llm_result['confidence']
            )

            # Calculate processing time
            processing_time_ms = (time.time() - entity_start_time) * 1000

            # Combine confidence scores
            combined_confidence = (
                llm_result['confidence'] * 0.7 +
                feature_vector.confidence_score * 0.3
            )

            return ImpactAssessmentResult(
                entity_id=entity_id,
                entity_type=entity_type.value,
                probabilities=probabilities,
                feature_vector=feature_vector,
                processing_time_ms=processing_time_ms,
                confidence_score=combined_confidence,
                reasoning=llm_result['reasoning']
            )

        except Exception as e:
            logger.error(f"Error assessing impact for {entity_id}: {e}")
            raise

    def _determine_entity_type(self, entity_id: str) -> EntityType:
        """Determine entity type from entity ID"""
        entity_id_upper = entity_id.upper()

        if any(currency in entity_id_upper for currency in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']):
            return EntityType.CURRENCY
        elif 'algo' in entity_id.lower():
            return EntityType.ALGORITHM
        elif 'option' in entity_id.lower() or 'future' in entity_id.lower():
            return EntityType.DERIVATIVE
        elif entity_id_upper in ['XAU', 'XAG', 'WTI', 'BTC']:
            return EntityType.COMMODITY
        else:
            return EntityType.CURRENCY  # Default

    def _create_empty_result(self, news_headline: str, start_time: float) -> NewsAnalysisResult:
        """Create empty result when no entities found"""
        return NewsAnalysisResult(
            news_headline=news_headline,
            analysis_timestamp=datetime.now(),
            semantic_event=None,
            entity_assessments=[],
            total_processing_time_ms=(time.time() - start_time) * 1000,
            entities_processed=0,
            overall_confidence=0.0,
            metadata={'error': 'No relevant entities found'}
        )

    def _create_error_result(self, news_headline: str, start_time: float, error: str) -> NewsAnalysisResult:
        """Create error result"""
        return NewsAnalysisResult(
            news_headline=news_headline,
            analysis_timestamp=datetime.now(),
            semantic_event=None,
            entity_assessments=[],
            total_processing_time_ms=(time.time() - start_time) * 1000,
            entities_processed=0,
            overall_confidence=0.0,
            metadata={'error': error}
        )

    def _update_stats(self, processing_time_ms: float, entities_processed: int):
        """Update performance statistics"""
        self.stats['analyses_completed'] += 1
        self.stats['total_processing_time'] += processing_time_ms
        self.stats['entities_processed'] += entities_processed
        self.stats['average_processing_time'] = (
            self.stats['total_processing_time'] / self.stats['analyses_completed']
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.stats.copy()

    def export_results_to_json(self, result: NewsAnalysisResult, filename: str = None) -> str:
        """Export analysis results to JSON"""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output/news_analysis_{timestamp}.json"

        # Convert result to serializable format
        export_data = {
            'news_headline': result.news_headline,
            'analysis_timestamp': result.analysis_timestamp.isoformat(),
            'total_processing_time_ms': result.total_processing_time_ms,
            'entities_processed': result.entities_processed,
            'overall_confidence': result.overall_confidence,
            'semantic_event': {
                'event_type': result.semantic_event.event_type.value if result.semantic_event else None,
                'severity': result.semantic_event.severity.value if result.semantic_event else None,
                'primary_entities': result.semantic_event.primary_entities if result.semantic_event else [],
                'confidence_score': result.semantic_event.confidence_score if result.semantic_event else 0.0
            } if result.semantic_event else None,
            'entity_assessments': [
                {
                    'entity_id': assessment.entity_id,
                    'entity_type': assessment.entity_type,
                    'probabilities': asdict(assessment.probabilities),
                    'processing_time_ms': assessment.processing_time_ms,
                    'confidence_score': assessment.confidence_score,
                    'feature_vector_summary': {
                        'feature_count': assessment.feature_vector.metadata['feature_count'],
                        'confidence': assessment.feature_vector.confidence_score
                    }
                }
                for assessment in result.entity_assessments
            ],
            'metadata': result.metadata
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        return filename


# Example usage and testing
async def run_poc_demo():
    """Demonstration of the POC system"""

    print("=== Financial News Impact Analysis POC ===\n")

    # Initialize POC system (configuration will determine mock vs real LLM)
    poc_assessor = POCImpactAssessor()

    # Test headlines
    test_headlines = [
        "Russia launches missile attack on Ukrainian energy infrastructure",
        "Federal Reserve raises interest rates by 0.75 basis points amid inflation concerns",
        "China announces new trade restrictions on semiconductor exports to Western countries",
        "ECB President signals potential emergency bond buying program",
        "OPEC+ announces surprise oil production cut of 2 million barrels per day"
    ]

    for i, headline in enumerate(test_headlines, 1):
        print(f"\n{i}. Analyzing: {headline}")
        print("-" * 80)

        # Analyze news impact
        result = await poc_assessor.analyze_news_impact(headline)

        print(f"Processing Time: {result.total_processing_time_ms:.1f}ms")
        print(f"Entities Processed: {result.entities_processed}")
        print(f"Overall Confidence: {result.overall_confidence:.3f}")

        if result.semantic_event:
            print(f"Event Type: {result.semantic_event.event_type.value}")
            print(f"Severity: {result.semantic_event.severity.value}")

        # Show top 3 entity assessments
        top_assessments = sorted(
            result.entity_assessments,
            key=lambda x: x.probabilities.case_3_major,
            reverse=True
        )[:3]

        print("\nTop Impact Assessments:")
        for assessment in top_assessments:
            probs = assessment.probabilities
            print(f"  {assessment.entity_id}:")
            print(f"    Major Impact: {probs.case_3_major:.3f}")
            print(f"    Moderate Impact: {probs.case_2_moderate:.3f}")
            print(f"    Minor Impact: {probs.case_1_minor:.3f}")
            print(f"    Confidence: {assessment.confidence_score:.3f}")

        # Export results
        filename = poc_assessor.export_results_to_json(result)
        print(f"\nResults exported to: {filename}")

    # Show overall performance statistics
    print("\n" + "="*80)
    print("Performance Statistics:")
    stats = poc_assessor.get_performance_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # Run the POC demonstration
    asyncio.run(run_poc_demo())