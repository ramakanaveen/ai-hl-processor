"""
Feature Engineering for Financial News Impact Analysis
Multi-dimensional feature extraction with economic context and causal reasoning
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class EntityType(Enum):
    CURRENCY = "currency"
    ALGORITHM = "algorithm"
    DERIVATIVE = "derivative"
    COMMODITY = "commodity"
    EQUITY_INDEX = "equity_index"


class FeatureCategory(Enum):
    NEWS_SEMANTIC = "news_semantic"
    ECONOMIC_CONTEXT = "economic_context"
    MARKET_DATA = "market_data"
    HISTORICAL_PATTERN = "historical_pattern"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    VOLATILITY = "volatility"


@dataclass
class FeatureVector:
    """Structured feature vector for model input"""
    entity_id: str
    entity_type: EntityType
    feature_categories: Dict[FeatureCategory, Dict[str, float]]
    feature_timestamp: datetime
    news_headline: str
    confidence_score: float
    metadata: Dict[str, Any]

    def to_array(self) -> np.ndarray:
        """Convert to flat numpy array for model input"""
        features = []
        for category, feature_dict in self.feature_categories.items():
            features.extend(feature_dict.values())
        return np.array(features, dtype=np.float32)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'entity_id': self.entity_id,
            'entity_type': self.entity_type.value,
            'features': {cat.value: features for cat, features in self.feature_categories.items()},
            'timestamp': self.feature_timestamp.isoformat(),
            'news_headline': self.news_headline,
            'confidence': self.confidence_score,
            'metadata': self.metadata
        }


class NewsSemanticFeatureExtractor:
    """Extract semantic features from news headlines"""

    def __init__(self):
        self.sentiment_keywords = self._load_sentiment_keywords()
        self.urgency_indicators = self._load_urgency_indicators()
        self.sector_keywords = self._load_sector_keywords()

    def _load_sentiment_keywords(self) -> Dict[str, List[str]]:
        """Load sentiment-related keywords"""
        return {
            'positive': [
                'boost', 'surge', 'rise', 'gain', 'improve', 'strengthen', 'rally',
                'optimistic', 'confident', 'stable', 'recovery', 'growth'
            ],
            'negative': [
                'crash', 'plunge', 'fall', 'decline', 'weaken', 'crisis', 'collapse',
                'recession', 'inflation', 'conflict', 'attack', 'sanction', 'embargo'
            ],
            'uncertainty': [
                'volatile', 'uncertain', 'unclear', 'speculation', 'rumor',
                'possibility', 'potential', 'concern', 'worry', 'risk'
            ]
        }

    def _load_urgency_indicators(self) -> Dict[str, float]:
        """Load words indicating urgency with weights"""
        return {
            'breaking': 1.0, 'urgent': 1.0, 'immediate': 0.9, 'emergency': 1.0,
            'sudden': 0.8, 'unexpected': 0.7, 'shock': 0.9, 'crisis': 0.8,
            'alert': 0.7, 'warning': 0.6, 'rapid': 0.6, 'quick': 0.5
        }

    def _load_sector_keywords(self) -> Dict[str, List[str]]:
        """Load sector-specific keywords"""
        return {
            'energy': ['oil', 'gas', 'energy', 'petroleum', 'coal', 'nuclear', 'renewable'],
            'financial': ['bank', 'credit', 'loan', 'interest', 'monetary', 'fiscal', 'fed'],
            'technology': ['tech', 'ai', 'semiconductor', 'chip', 'software', 'digital'],
            'agriculture': ['wheat', 'corn', 'agriculture', 'food', 'crop', 'harvest'],
            'manufacturing': ['factory', 'production', 'industrial', 'supply chain'],
            'commodities': ['gold', 'silver', 'copper', 'aluminum', 'commodity', 'metals']
        }

    def extract_features(self, news_text: str, semantic_event=None) -> Dict[str, float]:
        """Extract semantic features from news text"""
        text_lower = news_text.lower()
        features = {}

        # Basic text statistics
        features['text_length'] = len(news_text)
        features['word_count'] = len(news_text.split())
        features['sentence_count'] = len([s for s in news_text.split('.') if s.strip()])

        # Sentiment scoring
        sentiment_scores = self._calculate_sentiment_scores(text_lower)
        features.update(sentiment_scores)

        # Urgency scoring
        features['urgency_score'] = self._calculate_urgency_score(text_lower)

        # Sector exposure
        sector_scores = self._calculate_sector_exposure(text_lower)
        features.update(sector_scores)

        # Entity mention density
        features['entity_mention_density'] = self._calculate_entity_mention_density(text_lower)

        # Semantic event features if available
        if semantic_event:
            features.update(self._extract_semantic_event_features(semantic_event))

        return features

    def _calculate_sentiment_scores(self, text: str) -> Dict[str, float]:
        """Calculate sentiment scores based on keyword matching"""
        scores = {}
        total_words = len(text.split())

        for sentiment, keywords in self.sentiment_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text)
            scores[f'sentiment_{sentiment}'] = count / max(total_words, 1)

        # Net sentiment
        scores['net_sentiment'] = scores['sentiment_positive'] - scores['sentiment_negative']

        return scores

    def _calculate_urgency_score(self, text: str) -> float:
        """Calculate urgency score based on keywords"""
        urgency_score = 0.0
        for keyword, weight in self.urgency_indicators.items():
            if keyword in text:
                urgency_score += weight

        # Normalize by text length
        return min(urgency_score / len(text.split()), 1.0)

    def _calculate_sector_exposure(self, text: str) -> Dict[str, float]:
        """Calculate exposure to different economic sectors"""
        exposure = {}
        total_words = len(text.split())

        for sector, keywords in self.sector_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text)
            exposure[f'sector_{sector}'] = count / max(total_words, 1)

        return exposure

    def _calculate_entity_mention_density(self, text: str) -> float:
        """Calculate density of entity mentions (countries, companies, etc.)"""
        # Simple pattern matching for capitalized words (potential entities)
        words = text.split()
        capitalized_words = [w for w in words if w[0].isupper() and len(w) > 2]
        return len(capitalized_words) / max(len(words), 1)

    def _extract_semantic_event_features(self, semantic_event) -> Dict[str, float]:
        """Extract features from structured semantic event"""
        features = {}

        # Event type encoding (one-hot style)
        event_types = ['military_conflict', 'policy_change', 'economic_shock',
                      'natural_disaster', 'trade_dispute', 'central_bank_action']
        for event_type in event_types:
            features[f'event_type_{event_type}'] = float(semantic_event.event_type.value == event_type)

        # Severity encoding
        severity_map = {'low': 0.25, 'medium': 0.5, 'high': 0.75, 'critical': 1.0}
        features['event_severity'] = severity_map.get(semantic_event.severity.value, 0.5)

        # Time horizon encoding
        horizon_map = {'immediate': 1.0, 'short_term': 0.75, 'medium_term': 0.5, 'long_term': 0.25}
        features['event_time_horizon'] = horizon_map.get(semantic_event.time_horizon.value, 0.5)

        # Entity count features
        features['primary_entity_count'] = len(semantic_event.primary_entities)
        features['target_entity_count'] = len(semantic_event.target_entities)
        features['affected_sector_count'] = len(semantic_event.affected_sectors)

        return features


class EconomicContextFeatureExtractor:
    """Extract economic context features for entity-specific analysis"""

    def __init__(self, knowledge_base, market_data_client=None):
        self.knowledge_base = knowledge_base
        self.market_data_client = market_data_client

    def extract_features(self, entity_id: str, entity_type: EntityType,
                        semantic_event=None) -> Dict[str, float]:
        """Extract economic context features for specific entity"""

        features = {}

        # Get entity economic context
        entity_context = self.knowledge_base.get_entity_context(entity_id)

        # Basic economic indicators
        if 'economic_indicators' in entity_context:
            econ_features = self._extract_economic_indicator_features(entity_context['economic_indicators'])
            features.update(econ_features)

        # Trade relationship features
        trade_features = self._extract_trade_features(entity_context.get('trade_partners', {}))
        features.update(trade_features)

        # Supply chain features
        supply_chain_features = self._extract_supply_chain_features(
            entity_context.get('supply_chain_role', {})
        )
        features.update(supply_chain_features)

        # Currency group features
        currency_features = self._extract_currency_group_features(
            entity_context.get('currency_group', [])
        )
        features.update(currency_features)

        # Entity-type specific features
        if entity_type == EntityType.CURRENCY:
            features.update(self._extract_currency_specific_features(entity_id, semantic_event))
        elif entity_type == EntityType.ALGORITHM:
            features.update(self._extract_algorithm_specific_features(entity_id, semantic_event))
        elif entity_type == EntityType.DERIVATIVE:
            features.update(self._extract_derivative_specific_features(entity_id, semantic_event))

        return features

    def _extract_economic_indicator_features(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from economic indicators"""
        features = {}

        if not indicators:
            return features

        # Normalize economic indicators
        features['gdp_log'] = np.log(max(indicators.get('gdp_usd', 1e9), 1e9))
        features['trade_openness'] = indicators.get('trade_openness', 0.5)
        features['debt_to_gdp'] = min(indicators.get('debt_to_gdp', 0.6), 3.0)  # Cap at 300%
        features['inflation_rate'] = min(indicators.get('inflation_rate', 0.02), 0.5)  # Cap at 50%
        features['interest_rate'] = max(min(indicators.get('interest_rate', 0.02), 0.3), -0.1)

        # Economic stability indicators
        features['economic_stability'] = self._calculate_stability_score(indicators)

        return features

    def _calculate_stability_score(self, indicators: Dict[str, Any]) -> float:
        """Calculate economic stability score"""
        # Simple stability heuristic
        debt_penalty = min(indicators.get('debt_to_gdp', 0.6) / 2.0, 1.0)
        inflation_penalty = min(indicators.get('inflation_rate', 0.02) * 10, 1.0)

        stability = 1.0 - (debt_penalty * 0.4 + inflation_penalty * 0.6)
        return max(stability, 0.0)

    def _extract_trade_features(self, trade_partners: Dict[str, float]) -> Dict[str, float]:
        """Extract trade relationship features"""
        features = {}

        if not trade_partners:
            return {'trade_partner_count': 0.0, 'trade_concentration': 0.0}

        # Trade concentration measures
        trade_values = list(trade_partners.values())
        features['trade_partner_count'] = len(trade_partners)
        features['trade_concentration'] = np.sum(np.array(trade_values) ** 2)  # Herfindahl index
        features['max_trade_dependency'] = max(trade_values) if trade_values else 0.0
        features['trade_diversification'] = 1.0 - features['trade_concentration']

        # Major trading partner exposure
        major_economies = ['USA', 'China', 'Germany', 'Japan', 'UK']
        for economy in major_economies:
            features[f'trade_exposure_{economy.lower()}'] = trade_partners.get(economy, 0.0)

        return features

    def _extract_supply_chain_features(self, supply_chain_role: Dict[str, float]) -> Dict[str, float]:
        """Extract supply chain position features"""
        features = {}

        if not supply_chain_role:
            return {'supply_chain_importance': 0.0}

        # Calculate supply chain importance
        features['supply_chain_importance'] = sum(supply_chain_role.values())
        features['supply_chain_commodity_count'] = len(supply_chain_role)

        # Critical commodity exposure
        critical_commodities = ['crude_oil', 'natural_gas', 'semiconductors', 'rare_earth_metals']
        for commodity in critical_commodities:
            features[f'critical_supply_{commodity}'] = supply_chain_role.get(commodity, 0.0)

        return features

    def _extract_currency_group_features(self, currency_groups: List[str]) -> Dict[str, float]:
        """Extract currency group membership features"""
        features = {}

        # Binary indicators for currency group membership
        possible_groups = [
            'major_currencies', 'safe_haven_currencies', 'commodity_currencies',
            'emerging_market_currencies', 'risk_sensitive'
        ]

        for group in possible_groups:
            features[f'currency_group_{group}'] = float(group in currency_groups)

        return features

    def _extract_currency_specific_features(self, currency: str, semantic_event=None) -> Dict[str, float]:
        """Extract currency-specific features"""
        features = {}

        # Real-time market data features (mock implementation)
        if self.market_data_client:
            market_features = self._get_currency_market_features(currency)
            features.update(market_features)
        else:
            # Mock features for testing
            features.update({
                'current_volatility': 0.15,
                'volume_spike': 0.0,
                'momentum_1h': 0.0,
                'rsi_14d': 50.0
            })

        # Event-specific currency impact
        if semantic_event:
            features.update(self._calculate_currency_event_impact(currency, semantic_event))

        return features

    def _extract_algorithm_specific_features(self, algo_id: str, semantic_event=None) -> Dict[str, float]:
        """Extract algorithm-specific features"""
        features = {}

        # Mock algorithm performance features
        features.update({
            'current_pnl': 0.02,  # 2% return
            'max_drawdown': -0.05,  # 5% drawdown
            'volatility_target': 0.12,
            'current_leverage': 2.5,
            'position_count': 15,
            'concentration_risk': 0.3
        })

        # Market regime compatibility
        features.update({
            'trend_following_regime': 0.6,
            'mean_reversion_regime': 0.4,
            'high_vol_regime': 0.7,
            'correlation_regime': 0.5
        })

        return features

    def _extract_derivative_specific_features(self, derivative_id: str, semantic_event=None) -> Dict[str, float]:
        """Extract derivative-specific features"""
        features = {}

        # Mock derivative risk features
        features.update({
            'delta_exposure': 0.15,
            'gamma_exposure': 0.05,
            'vega_exposure': -0.08,
            'theta_decay': -0.02,
            'implied_volatility': 0.22,
            'time_to_expiry': 30.0,  # days
            'moneyness': 1.02  # spot/strike ratio
        })

        # Underlying asset features
        features.update({
            'underlying_volatility': 0.18,
            'underlying_momentum': 0.05,
            'correlation_breakdown': 0.0
        })

        return features

    def _get_currency_market_features(self, currency: str) -> Dict[str, float]:
        """Get real-time market features for currency (mock implementation)"""
        # In production, integrate with market data provider
        return {
            'bid_ask_spread': 0.0002,
            'volume_1h': 1000000,
            'price_change_1h': 0.0015,
            'volatility_1h': 0.008,
            'order_book_imbalance': 0.1
        }

    def _calculate_currency_event_impact(self, currency: str, semantic_event) -> Dict[str, float]:
        """Calculate event-specific impact on currency"""
        features = {}

        # Determine if currency is directly mentioned in event
        currency_mentioned = currency in ' '.join(semantic_event.primary_entities + semantic_event.target_entities)
        features['direct_mention'] = float(currency_mentioned)

        # Safe haven flow potential
        safe_haven_currencies = ['USD', 'JPY', 'CHF']
        if currency in safe_haven_currencies and semantic_event.event_type.value in ['military_conflict', 'economic_shock']:
            features['safe_haven_flow_potential'] = 1.0
        else:
            features['safe_haven_flow_potential'] = 0.0

        # Risk-off sensitivity
        risk_sensitive_currencies = ['AUD', 'NZD', 'BRL', 'MXN', 'ZAR']
        if currency in risk_sensitive_currencies:
            features['risk_off_sensitivity'] = 1.0
        else:
            features['risk_off_sensitivity'] = 0.0

        return features


class ContextualFeatureBuilder:
    """Main feature builder that combines all feature extractors"""

    def __init__(self, knowledge_base, market_data_client=None):
        self.news_extractor = NewsSemanticFeatureExtractor()
        self.economic_extractor = EconomicContextFeatureExtractor(knowledge_base, market_data_client)
        self.feature_cache = {}

    def build_features(self, news_headline: str, entity_id: str, entity_type: EntityType,
                      semantic_event=None, use_cache: bool = True) -> FeatureVector:
        """Build complete feature vector for entity-news pair"""

        # Generate cache key
        cache_key = self._generate_cache_key(news_headline, entity_id, entity_type.value)

        if use_cache and cache_key in self.feature_cache:
            logger.debug(f"Using cached features for {entity_id}")
            return self.feature_cache[cache_key]

        # Extract semantic features from news
        news_features = self.news_extractor.extract_features(news_headline, semantic_event)

        # Extract economic context features
        economic_features = self.economic_extractor.extract_features(entity_id, entity_type, semantic_event)

        # Add interaction features
        interaction_features = self._create_interaction_features(news_features, economic_features)

        # Organize features by category
        feature_categories = {
            FeatureCategory.NEWS_SEMANTIC: news_features,
            FeatureCategory.ECONOMIC_CONTEXT: economic_features,
            FeatureCategory.MARKET_DATA: self._extract_market_data_features(entity_id, entity_type),
            FeatureCategory.HISTORICAL_PATTERN: self._extract_historical_features(entity_id, news_headline),
            FeatureCategory.SENTIMENT: self._extract_sentiment_features(news_headline),
            FeatureCategory.TECHNICAL: interaction_features
        }

        # Calculate confidence score
        confidence_score = self._calculate_feature_confidence(feature_categories, semantic_event)

        # Create feature vector
        feature_vector = FeatureVector(
            entity_id=entity_id,
            entity_type=entity_type,
            feature_categories=feature_categories,
            feature_timestamp=datetime.now(),
            news_headline=news_headline,
            confidence_score=confidence_score,
            metadata={
                'feature_count': sum(len(features) for features in feature_categories.values()),
                'has_semantic_event': semantic_event is not None,
                'cache_key': cache_key
            }
        )

        # Cache result
        if use_cache:
            self.feature_cache[cache_key] = feature_vector

        return feature_vector

    def _generate_cache_key(self, news_headline: str, entity_id: str, entity_type: str) -> str:
        """Generate cache key for feature vector"""
        content = f"{news_headline}|{entity_id}|{entity_type}"
        return hashlib.md5(content.encode()).hexdigest()

    def _create_interaction_features(self, news_features: Dict[str, float],
                                   economic_features: Dict[str, float]) -> Dict[str, float]:
        """Create interaction features between news and economic context"""
        interactions = {}

        # News sentiment x economic stability
        news_sentiment = news_features.get('net_sentiment', 0.0)
        economic_stability = economic_features.get('economic_stability', 0.5)
        interactions['sentiment_stability_interaction'] = news_sentiment * economic_stability

        # Urgency x trade concentration
        urgency = news_features.get('urgency_score', 0.0)
        trade_concentration = economic_features.get('trade_concentration', 0.0)
        interactions['urgency_concentration_interaction'] = urgency * trade_concentration

        # Event severity x supply chain importance
        event_severity = news_features.get('event_severity', 0.5)
        supply_importance = economic_features.get('supply_chain_importance', 0.0)
        interactions['severity_supply_interaction'] = event_severity * supply_importance

        return interactions

    def _extract_market_data_features(self, entity_id: str, entity_type: EntityType) -> Dict[str, float]:
        """Extract real-time market data features (mock implementation)"""
        # In production, integrate with market data feeds
        return {
            'current_price': 1.0,
            'volume_ratio': 1.2,
            'volatility_regime': 0.6,
            'correlation_level': 0.75
        }

    def _extract_historical_features(self, entity_id: str, news_headline: str) -> Dict[str, float]:
        """Extract historical pattern features (mock implementation)"""
        # In production, query historical news-impact database
        return {
            'similar_news_count': 5.0,
            'historical_impact_avg': 0.15,
            'pattern_confidence': 0.7,
            'recency_weight': 0.8
        }

    def _extract_sentiment_features(self, news_headline: str) -> Dict[str, float]:
        """Extract advanced sentiment features"""
        # Could integrate with more sophisticated sentiment analysis
        return {
            'compound_sentiment': 0.1,
            'sentiment_magnitude': 0.6,
            'emotional_intensity': 0.4
        }

    def _calculate_feature_confidence(self, feature_categories: Dict[FeatureCategory, Dict[str, float]],
                                    semantic_event=None) -> float:
        """Calculate overall confidence in the feature extraction"""

        confidence_factors = []

        # Feature completeness
        total_features = sum(len(features) for features in feature_categories.values())
        feature_completeness = min(total_features / 50.0, 1.0)  # Expect ~50 features
        confidence_factors.append(feature_completeness)

        # Semantic event availability
        if semantic_event:
            confidence_factors.append(semantic_event.confidence_score)
        else:
            confidence_factors.append(0.6)  # Lower confidence without semantic analysis

        # Data quality indicators
        nan_count = sum(
            1 for features in feature_categories.values()
            for value in features.values()
            if np.isnan(value) or np.isinf(value)
        )
        data_quality = 1.0 - (nan_count / max(total_features, 1))
        confidence_factors.append(data_quality)

        return np.mean(confidence_factors)

    def batch_build_features(self, news_headline: str, entities: List[Tuple[str, EntityType]],
                           semantic_event=None) -> List[FeatureVector]:
        """Build features for multiple entities efficiently"""

        feature_vectors = []

        for entity_id, entity_type in entities:
            try:
                feature_vector = self.build_features(
                    news_headline, entity_id, entity_type, semantic_event
                )
                feature_vectors.append(feature_vector)
            except Exception as e:
                logger.error(f"Error building features for {entity_id}: {e}")
                continue

        return feature_vectors

    def clear_cache(self):
        """Clear feature cache"""
        self.feature_cache.clear()

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores (mock implementation)"""
        # In production, could be learned from model training
        return {
            'event_severity': 0.15,
            'trade_concentration': 0.12,
            'sentiment_negative': 0.10,
            'urgency_score': 0.09,
            'economic_stability': 0.08,
            'supply_chain_importance': 0.07
        }


# Example usage and testing
if __name__ == "__main__":
    from economic_knowledge_graph import EconomicKnowledgeBase

    def test_feature_engineering():
        """Test the feature engineering pipeline"""

        # Initialize components
        kb = EconomicKnowledgeBase()
        feature_builder = ContextualFeatureBuilder(kb)

        print("=== Feature Engineering Test ===\n")

        # Test news headline
        news_headline = "Russia launches missile attack on Ukrainian energy infrastructure"

        # Test entities
        test_entities = [
            ('EURUSD', EntityType.CURRENCY),
            ('momentum_algo_1', EntityType.ALGORITHM),
            ('fx_option_eurusd', EntityType.DERIVATIVE)
        ]

        print(f"Processing news: {news_headline}\n")

        for entity_id, entity_type in test_entities:
            print(f"--- Features for {entity_id} ({entity_type.value}) ---")

            feature_vector = feature_builder.build_features(
                news_headline, entity_id, entity_type
            )

            print(f"Total features: {feature_vector.metadata['feature_count']}")
            print(f"Confidence: {feature_vector.confidence_score:.3f}")
            print(f"Feature array shape: {feature_vector.to_array().shape}")

            # Show sample features from each category
            for category, features in feature_vector.feature_categories.items():
                if features:
                    sample_features = list(features.items())[:3]
                    print(f"  {category.value}: {sample_features}")

            print()

        # Test batch processing
        print("--- Batch Processing Test ---")
        batch_features = feature_builder.batch_build_features(
            news_headline, test_entities
        )
        print(f"Processed {len(batch_features)} entities in batch")

        # Feature importance
        print("--- Feature Importance ---")
        importance = feature_builder.get_feature_importance()
        for feature, score in list(importance.items())[:5]:
            print(f"  {feature}: {score:.3f}")

    test_feature_engineering()