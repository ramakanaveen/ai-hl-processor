"""
Semantic Impact Analysis Engine for Financial News
Processes Bloomberg headlines to extract semantic meaning and assess multi-dimensional impact
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    MILITARY_CONFLICT = "military_conflict"
    POLICY_CHANGE = "policy_change"
    ECONOMIC_SHOCK = "economic_shock"
    NATURAL_DISASTER = "natural_disaster"
    TRADE_DISPUTE = "trade_dispute"
    CENTRAL_BANK_ACTION = "central_bank_action"
    POLITICAL_INSTABILITY = "political_instability"
    COMMODITY_SHOCK = "commodity_shock"


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TimeHorizon(Enum):
    IMMEDIATE = "immediate"  # 0-2 hours
    SHORT_TERM = "short_term"  # 2-24 hours
    MEDIUM_TERM = "medium_term"  # 1-7 days
    LONG_TERM = "long_term"  # 1+ weeks


@dataclass
class SemanticEvent:
    """Structured representation of a news event"""
    event_type: EventType
    primary_entities: List[str]
    target_entities: List[str]
    affected_sectors: List[str]
    severity: SeverityLevel
    time_horizon: TimeHorizon
    economic_effects: List[str]
    confidence_score: float
    raw_text: str
    timestamp: datetime


@dataclass
class ImpactProbabilities:
    """Impact assessment probabilities for different scenarios"""
    abstain: float
    case_1_minor: float
    case_2_moderate: float
    case_3_major: float
    reasoning: str
    confidence: float


class SemanticNewsAnalyzer:
    """Extracts semantic meaning and structured events from news headlines"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.event_patterns = self._load_event_patterns()

    def _load_event_patterns(self) -> Dict[str, List[str]]:
        """Load predefined patterns for quick event classification"""
        return {
            "conflict_keywords": [
                "attack", "war", "invasion", "missile", "bombing", "conflict",
                "sanctions", "embargo", "blockade", "military action"
            ],
            "economic_keywords": [
                "inflation", "recession", "gdp", "unemployment", "interest rate",
                "monetary policy", "fiscal policy", "budget", "debt", "default"
            ],
            "trade_keywords": [
                "tariff", "trade war", "export", "import", "trade deal",
                "wto", "free trade", "protectionism", "quota"
            ],
            "energy_keywords": [
                "oil", "gas", "energy", "pipeline", "opec", "crude",
                "renewable", "nuclear", "coal", "electricity"
            ]
        }

    async def extract_events(self, news_text: str) -> SemanticEvent:
        """Extract structured events from news headline"""

        # Quick pattern-based classification
        event_type = self._classify_event_type(news_text)

        # If LLM available, use for detailed extraction
        if self.llm_client:
            structured_event = await self._llm_extract_events(news_text, event_type)
        else:
            structured_event = self._rule_based_extraction(news_text, event_type)

        return structured_event

    def _classify_event_type(self, news_text: str) -> EventType:
        """Quick rule-based event type classification"""
        text_lower = news_text.lower()

        if any(keyword in text_lower for keyword in self.event_patterns["conflict_keywords"]):
            return EventType.MILITARY_CONFLICT
        elif any(keyword in text_lower for keyword in self.event_patterns["economic_keywords"]):
            return EventType.ECONOMIC_SHOCK
        elif any(keyword in text_lower for keyword in self.event_patterns["trade_keywords"]):
            return EventType.TRADE_DISPUTE
        else:
            return EventType.POLICY_CHANGE

    async def _llm_extract_events(self, news_text: str, event_type: EventType) -> SemanticEvent:
        """Use LLM for detailed semantic extraction"""

        prompt = f"""
        Extract structured events from this financial news headline:
        "{news_text}"

        Preliminary classification: {event_type.value}

        Return JSON with:
        - event_type: one of [military_conflict, policy_change, economic_shock, natural_disaster, trade_dispute, central_bank_action, political_instability, commodity_shock]
        - primary_entities: list of main countries/companies/organizations involved
        - target_entities: list of entities being affected
        - affected_sectors: list of economic sectors [energy, agriculture, manufacturing, finance, technology, commodities, etc.]
        - severity: one of [low, medium, high, critical]
        - time_horizon: one of [immediate, short_term, medium_term, long_term]
        - economic_effects: list of effects [supply_disruption, demand_shock, currency_pressure, commodity_price_spike, risk_off_sentiment, etc.]
        - confidence_score: float between 0-1

        Focus on economic and financial implications.
        """

        try:
            # Placeholder for LLM call - replace with actual implementation
            response = await self._mock_llm_call(prompt)
            return self._parse_llm_response(response, news_text)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, falling back to rule-based")
            return self._rule_based_extraction(news_text, event_type)

    async def _mock_llm_call(self, prompt: str) -> Dict[str, Any]:
        """Mock LLM call for testing - replace with actual LLM implementation"""
        await asyncio.sleep(0.1)  # Simulate API call
        return {
            "event_type": "military_conflict",
            "primary_entities": ["Russia"],
            "target_entities": ["Ukraine"],
            "affected_sectors": ["energy", "agriculture", "commodities"],
            "severity": "high",
            "time_horizon": "immediate",
            "economic_effects": ["supply_disruption", "commodity_price_spike", "risk_off_sentiment"],
            "confidence_score": 0.85
        }

    def _parse_llm_response(self, response: Dict[str, Any], news_text: str) -> SemanticEvent:
        """Parse LLM response into SemanticEvent object"""
        return SemanticEvent(
            event_type=EventType(response.get("event_type", "policy_change")),
            primary_entities=response.get("primary_entities", []),
            target_entities=response.get("target_entities", []),
            affected_sectors=response.get("affected_sectors", []),
            severity=SeverityLevel(response.get("severity", "medium")),
            time_horizon=TimeHorizon(response.get("time_horizon", "short_term")),
            economic_effects=response.get("economic_effects", []),
            confidence_score=response.get("confidence_score", 0.5),
            raw_text=news_text,
            timestamp=datetime.now()
        )

    def _rule_based_extraction(self, news_text: str, event_type: EventType) -> SemanticEvent:
        """Fallback rule-based extraction"""
        return SemanticEvent(
            event_type=event_type,
            primary_entities=self._extract_entities(news_text),
            target_entities=[],
            affected_sectors=self._extract_sectors(news_text),
            severity=SeverityLevel.MEDIUM,
            time_horizon=TimeHorizon.SHORT_TERM,
            economic_effects=["market_volatility"],
            confidence_score=0.6,
            raw_text=news_text,
            timestamp=datetime.now()
        )

    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction - replace with proper NER"""
        # Common country/entity patterns
        entities = []
        common_entities = [
            "USA", "US", "China", "Russia", "Germany", "Japan", "UK", "France",
            "Fed", "ECB", "BOJ", "BOE", "IMF", "World Bank", "OPEC"
        ]

        for entity in common_entities:
            if entity.lower() in text.lower():
                entities.append(entity)

        return entities

    def _extract_sectors(self, text: str) -> List[str]:
        """Extract affected economic sectors"""
        sectors = []
        sector_keywords = {
            "energy": ["oil", "gas", "energy", "petroleum"],
            "agriculture": ["wheat", "corn", "agriculture", "food"],
            "finance": ["bank", "financial", "credit", "loan"],
            "technology": ["tech", "semiconductor", "software"],
            "manufacturing": ["factory", "production", "manufacturing"]
        }

        text_lower = text.lower()
        for sector, keywords in sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                sectors.append(sector)

        return sectors or ["general"]


class ImpactPropagationEngine:
    """Propagates impact through economic relationships"""

    def __init__(self, economic_graph):
        self.economic_graph = economic_graph

    async def propagate_impact(self, semantic_event: SemanticEvent) -> Dict[str, List[Dict]]:
        """Propagate impact through economic relationship network"""

        impact_cascade = {
            'direct_impacts': [],
            'first_order_impacts': [],
            'second_order_impacts': []
        }

        # Direct impacts on primary entities
        for entity in semantic_event.primary_entities:
            direct_impact = self._calculate_direct_impact(semantic_event, entity)
            impact_cascade['direct_impacts'].append(direct_impact)

            # First-order propagation
            related_entities = self.economic_graph.get_related_entities(entity)
            for related_entity, relationship in related_entities.items():
                first_order_impact = self._calculate_propagated_impact(
                    semantic_event, entity, related_entity, relationship
                )
                impact_cascade['first_order_impacts'].append(first_order_impact)

        return impact_cascade

    def _calculate_direct_impact(self, event: SemanticEvent, entity: str) -> Dict:
        """Calculate direct impact on an entity"""
        severity_multiplier = {
            SeverityLevel.LOW: 0.3,
            SeverityLevel.MEDIUM: 0.6,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.CRITICAL: 1.0
        }

        base_impact = severity_multiplier[event.severity]

        return {
            'entity': entity,
            'impact_type': 'direct',
            'severity_score': base_impact,
            'affected_areas': event.affected_sectors,
            'reasoning': f"Direct impact from {event.event_type.value}"
        }

    def _calculate_propagated_impact(self, event: SemanticEvent, source_entity: str,
                                   target_entity: str, relationship: Dict) -> Dict:
        """Calculate propagated impact through relationships"""

        # Decay impact based on relationship strength and distance
        relationship_strength = relationship.get('strength', 0.5)
        propagated_severity = event.severity.value

        # Apply decay factor
        decay_factor = relationship_strength * 0.7  # Propagation reduces impact

        return {
            'entity': target_entity,
            'impact_type': 'propagated',
            'severity_score': decay_factor,
            'relationship_type': relationship.get('type', 'trade'),
            'source_entity': source_entity,
            'reasoning': f"Impact propagated via {relationship.get('type', 'economic')} relationship"
        }


class SemanticImpactEngine:
    """Main engine coordinating semantic analysis and impact assessment"""

    def __init__(self, llm_client=None, economic_graph=None):
        self.semantic_analyzer = SemanticNewsAnalyzer(llm_client)
        self.impact_propagator = ImpactPropagationEngine(economic_graph)
        self.economic_graph = economic_graph

    async def analyze_news_impact(self, news_headline: str) -> Dict[str, Any]:
        """Complete semantic analysis and impact assessment"""

        try:
            # Step 1: Extract semantic events
            semantic_event = await self.semantic_analyzer.extract_events(news_headline)

            # Step 2: Propagate impact through economic network
            impact_cascade = await self.impact_propagator.propagate_impact(semantic_event)

            # Step 3: Generate entity-specific assessments
            entity_assessments = await self._generate_entity_assessments(
                semantic_event, impact_cascade
            )

            return {
                'semantic_event': semantic_event,
                'impact_cascade': impact_cascade,
                'entity_assessments': entity_assessments,
                'processing_time': datetime.now(),
                'confidence': semantic_event.confidence_score
            }

        except Exception as e:
            logger.error(f"Error in semantic impact analysis: {e}")
            return {
                'error': str(e),
                'semantic_event': None,
                'impact_cascade': {},
                'entity_assessments': {},
                'processing_time': datetime.now(),
                'confidence': 0.0
            }

    async def _generate_entity_assessments(self, semantic_event: SemanticEvent,
                                         impact_cascade: Dict) -> Dict[str, ImpactProbabilities]:
        """Generate probability assessments for each affected entity"""

        assessments = {}

        # Assess direct impacts
        for direct_impact in impact_cascade['direct_impacts']:
            entity = direct_impact['entity']
            assessment = self._calculate_impact_probabilities(
                semantic_event, direct_impact['severity_score'], 'direct'
            )
            assessments[entity] = assessment

        # Assess propagated impacts
        for propagated_impact in impact_cascade['first_order_impacts']:
            entity = propagated_impact['entity']
            if entity not in assessments:  # Don't override direct impacts
                assessment = self._calculate_impact_probabilities(
                    semantic_event, propagated_impact['severity_score'], 'propagated'
                )
                assessments[entity] = assessment

        return assessments

    def _calculate_impact_probabilities(self, event: SemanticEvent,
                                      severity_score: float, impact_type: str) -> ImpactProbabilities:
        """Calculate probability distribution for impact scenarios"""

        # Base probabilities based on severity
        if severity_score >= 0.8:  # High severity
            probs = [0.1, 0.2, 0.3, 0.4]  # [abstain, minor, moderate, major]
        elif severity_score >= 0.6:  # Medium-high severity
            probs = [0.15, 0.25, 0.4, 0.2]
        elif severity_score >= 0.4:  # Medium severity
            probs = [0.2, 0.4, 0.3, 0.1]
        else:  # Low severity
            probs = [0.4, 0.4, 0.15, 0.05]

        # Adjust for impact type
        if impact_type == 'propagated':
            # Shift towards lower impact for propagated effects
            probs = [probs[0] + 0.1, probs[1] + 0.1, probs[2] - 0.1, probs[3] - 0.1]

        # Normalize to ensure sum = 1
        probs = np.array(probs)
        probs = probs / probs.sum()

        reasoning = f"{impact_type.title()} impact from {event.event_type.value}. Severity: {severity_score:.2f}"

        return ImpactProbabilities(
            abstain=probs[0],
            case_1_minor=probs[1],
            case_2_moderate=probs[2],
            case_3_major=probs[3],
            reasoning=reasoning,
            confidence=event.confidence_score * 0.9 if impact_type == 'propagated' else event.confidence_score
        )


# Example usage and testing
if __name__ == "__main__":
    async def test_semantic_engine():
        """Test the semantic impact engine"""

        # Initialize engine (without LLM for testing)
        engine = SemanticImpactEngine()

        # Test headlines
        test_headlines = [
            "Russia launches missile attack on Ukrainian energy infrastructure",
            "Federal Reserve raises interest rates by 0.75 basis points",
            "China imposes trade restrictions on semiconductor exports",
            "ECB announces emergency bond buying program"
        ]

        for headline in test_headlines:
            print(f"\n--- Analyzing: {headline} ---")

            result = await engine.analyze_news_impact(headline)

            if result.get('semantic_event'):
                event = result['semantic_event']
                print(f"Event Type: {event.event_type.value}")
                print(f"Primary Entities: {event.primary_entities}")
                print(f"Affected Sectors: {event.affected_sectors}")
                print(f"Severity: {event.severity.value}")
                print(f"Confidence: {event.confidence_score}")

                # Print entity assessments
                for entity, assessment in result['entity_assessments'].items():
                    print(f"\n{entity} Impact Assessment:")
                    print(f"  Abstain: {assessment.abstain:.2f}")
                    print(f"  Minor: {assessment.case_1_minor:.2f}")
                    print(f"  Moderate: {assessment.case_2_moderate:.2f}")
                    print(f"  Major: {assessment.case_3_major:.2f}")
                    print(f"  Reasoning: {assessment.reasoning}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")

    # Run test
    asyncio.run(test_semantic_engine())