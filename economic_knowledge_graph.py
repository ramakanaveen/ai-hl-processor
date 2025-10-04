"""
Economic Knowledge Graph and Relationship Management
Manages economic relationships, trade dependencies, and impact propagation paths
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    TRADE_PARTNER = "trade_partner"
    ENERGY_SUPPLIER = "energy_supplier"
    FINANCIAL_CORRELATION = "financial_correlation"
    SUPPLY_CHAIN = "supply_chain"
    CURRENCY_DEPENDENCY = "currency_dependency"
    SAFE_HAVEN_FLOW = "safe_haven_flow"
    COMMODITY_PRODUCER = "commodity_producer"
    GEOPOLITICAL_ALLIANCE = "geopolitical_alliance"


@dataclass
class EconomicRelationship:
    """Represents an economic relationship between two entities"""
    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    strength: float  # 0.0 to 1.0
    direction: str  # "bilateral", "unidirectional"
    sectors: List[str]
    dependency_score: float  # How dependent target is on source
    volatility_transmission: float  # How much volatility transmits
    metadata: Dict[str, Any]


@dataclass
class EconomicIndicators:
    """Key economic indicators for an entity"""
    entity: str
    gdp_usd: float
    trade_openness: float  # (Exports + Imports) / GDP
    currency_reserves: float
    debt_to_gdp: float
    inflation_rate: float
    interest_rate: float
    commodity_dependence: Dict[str, float]
    last_updated: datetime


class EconomicKnowledgeBase:
    """Manages static economic knowledge and relationships"""

    def __init__(self):
        self.trade_relationships = self._initialize_trade_relationships()
        self.supply_chain_dependencies = self._initialize_supply_chain_data()
        self.currency_correlations = self._initialize_currency_correlations()
        self.commodity_dependencies = self._initialize_commodity_dependencies()
        self.safe_haven_hierarchies = self._initialize_safe_haven_data()
        self.economic_indicators = self._initialize_economic_indicators()

    def _initialize_trade_relationships(self) -> Dict[str, Dict[str, float]]:
        """Initialize bilateral trade relationship matrix"""
        return {
            'USA': {
                'China': 0.18, 'Canada': 0.15, 'Mexico': 0.14, 'Germany': 0.06,
                'Japan': 0.06, 'UK': 0.05, 'South Korea': 0.04, 'India': 0.04
            },
            'China': {
                'USA': 0.18, 'Germany': 0.08, 'Japan': 0.07, 'South Korea': 0.06,
                'Australia': 0.05, 'India': 0.05, 'Russia': 0.04, 'Brazil': 0.03
            },
            'Germany': {
                'USA': 0.06, 'China': 0.08, 'France': 0.09, 'Netherlands': 0.07,
                'Italy': 0.06, 'UK': 0.06, 'Poland': 0.05, 'Austria': 0.04
            },
            'Russia': {
                'China': 0.19, 'Germany': 0.08, 'Turkey': 0.05, 'Italy': 0.04,
                'India': 0.04, 'South Korea': 0.03, 'Japan': 0.03, 'USA': 0.02
            },
            'Japan': {
                'China': 0.23, 'USA': 0.15, 'South Korea': 0.06, 'Australia': 0.04,
                'Germany': 0.04, 'Taiwan': 0.04, 'India': 0.03, 'Thailand': 0.03
            },
            'UK': {
                'USA': 0.13, 'Germany': 0.11, 'China': 0.07, 'France': 0.06,
                'Netherlands': 0.06, 'Ireland': 0.05, 'Italy': 0.04, 'Spain': 0.04
            }
        }

    def _initialize_supply_chain_data(self) -> Dict[str, Dict[str, float]]:
        """Initialize critical supply chain dependencies"""
        return {
            'semiconductors': {
                'Taiwan': 0.63, 'South Korea': 0.18, 'China': 0.12, 'Japan': 0.04, 'USA': 0.03
            },
            'rare_earth_metals': {
                'China': 0.80, 'Australia': 0.08, 'USA': 0.05, 'Myanmar': 0.03, 'Russia': 0.02
            },
            'wheat': {
                'Russia': 0.18, 'Ukraine': 0.12, 'USA': 0.14, 'Canada': 0.08, 'Australia': 0.06
            },
            'corn': {
                'USA': 0.32, 'Argentina': 0.17, 'Brazil': 0.15, 'Ukraine': 0.16, 'China': 0.08
            },
            'crude_oil': {
                'Saudi Arabia': 0.12, 'Russia': 0.11, 'USA': 0.11, 'Iraq': 0.05, 'UAE': 0.04
            },
            'natural_gas': {
                'Russia': 0.17, 'USA': 0.16, 'Qatar': 0.05, 'Australia': 0.04, 'Norway': 0.04
            },
            'lithium': {
                'Australia': 0.52, 'Chile': 0.26, 'China': 0.13, 'Argentina': 0.06, 'Zimbabwe': 0.02
            },
            'neon_gas': {
                'Ukraine': 0.70, 'Russia': 0.20, 'China': 0.08, 'USA': 0.02
            }
        }

    def _initialize_currency_correlations(self) -> Dict[str, List[str]]:
        """Initialize currency correlation groups"""
        return {
            'major_currencies': ['USD', 'EUR', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'NZD'],
            'safe_haven_currencies': ['USD', 'JPY', 'CHF', 'EUR'],
            'commodity_currencies': ['AUD', 'CAD', 'NOK', 'NZD', 'ZAR', 'BRL'],
            'emerging_market_currencies': ['BRL', 'MXN', 'ZAR', 'TRY', 'INR', 'CNY', 'RUB'],
            'oil_linked_currencies': ['CAD', 'NOK', 'RUB', 'MXN'],
            'gold_correlated': ['AUD', 'ZAR', 'CHF'],
            'risk_sensitive': ['AUD', 'NZD', 'BRL', 'MXN', 'ZAR', 'TRY']
        }

    def _initialize_commodity_dependencies(self) -> Dict[str, Dict[str, float]]:
        """Initialize commodity export dependencies by country"""
        return {
            'Russia': {
                'crude_oil': 0.25, 'natural_gas': 0.15, 'wheat': 0.08, 'gold': 0.04,
                'aluminum': 0.03, 'nickel': 0.02, 'uranium': 0.02
            },
            'Saudi Arabia': {
                'crude_oil': 0.75, 'petrochemicals': 0.08, 'natural_gas': 0.05
            },
            'Australia': {
                'iron_ore': 0.22, 'coal': 0.15, 'gold': 0.08, 'lithium': 0.04,
                'natural_gas': 0.12, 'aluminum': 0.03
            },
            'Chile': {
                'copper': 0.45, 'lithium': 0.08, 'gold': 0.04, 'wine': 0.03
            },
            'Norway': {
                'crude_oil': 0.35, 'natural_gas': 0.25, 'seafood': 0.08, 'aluminum': 0.04
            },
            'Brazil': {
                'iron_ore': 0.12, 'soybeans': 0.11, 'crude_oil': 0.09, 'coffee': 0.04,
                'corn': 0.04, 'sugar': 0.03
            }
        }

    def _initialize_safe_haven_data(self) -> Dict[str, float]:
        """Initialize safe haven flow patterns"""
        return {
            'USD': 0.45,  # Primary safe haven
            'JPY': 0.25,  # Secondary safe haven
            'CHF': 0.15,  # European safe haven
            'EUR': 0.10,  # Conditional safe haven
            'Gold': 0.35,  # Commodity safe haven
            'US_Treasuries': 0.50,  # Bond safe haven
            'German_Bunds': 0.20,  # European bond safe haven
            'Japanese_JGBs': 0.15   # Asian bond safe haven
        }

    def _initialize_economic_indicators(self) -> Dict[str, EconomicIndicators]:
        """Initialize economic indicators for major entities"""
        return {
            'USA': EconomicIndicators(
                entity='USA', gdp_usd=25.4e12, trade_openness=0.27, currency_reserves=0.24e12,
                debt_to_gdp=1.28, inflation_rate=0.032, interest_rate=0.055,
                commodity_dependence={'oil': 0.15, 'agriculture': 0.12},
                last_updated=datetime.now()
            ),
            'China': EconomicIndicators(
                entity='China', gdp_usd=17.7e12, trade_openness=0.38, currency_reserves=3.2e12,
                debt_to_gdp=0.72, inflation_rate=0.021, interest_rate=0.035,
                commodity_dependence={'oil': 0.25, 'iron_ore': 0.18, 'soybeans': 0.08},
                last_updated=datetime.now()
            ),
            'Germany': EconomicIndicators(
                entity='Germany', gdp_usd=4.2e12, trade_openness=0.94, currency_reserves=0.25e12,
                debt_to_gdp=0.69, inflation_rate=0.028, interest_rate=0.035,
                commodity_dependence={'oil': 0.22, 'natural_gas': 0.18},
                last_updated=datetime.now()
            ),
            'Russia': EconomicIndicators(
                entity='Russia', gdp_usd=2.1e12, trade_openness=0.46, currency_reserves=0.58e12,
                debt_to_gdp=0.19, inflation_rate=0.058, interest_rate=0.165,
                commodity_dependence={'oil': 0.35, 'natural_gas': 0.25, 'wheat': 0.08},
                last_updated=datetime.now()
            ),
            'Japan': EconomicIndicators(
                entity='Japan', gdp_usd=4.9e12, trade_openness=0.37, currency_reserves=1.3e12,
                debt_to_gdp=2.64, inflation_rate=0.024, interest_rate=-0.001,
                commodity_dependence={'oil': 0.28, 'natural_gas': 0.15, 'coal': 0.12},
                last_updated=datetime.now()
            )
        }

    def get_entity_context(self, entity: str) -> Dict[str, Any]:
        """Get comprehensive economic context for an entity"""
        context = {
            'entity': entity,
            'trade_partners': self.trade_relationships.get(entity, {}),
            'economic_indicators': asdict(self.economic_indicators.get(entity)) if entity in self.economic_indicators else {},
            'commodity_exports': self.commodity_dependencies.get(entity, {}),
            'currency_group': self._get_currency_group(entity),
            'supply_chain_role': self._get_supply_chain_role(entity)
        }
        return context

    def _get_currency_group(self, entity: str) -> List[str]:
        """Determine which currency groups an entity belongs to"""
        # Map entity to currency code
        entity_to_currency = {
            'USA': 'USD', 'Germany': 'EUR', 'Japan': 'JPY', 'UK': 'GBP',
            'Switzerland': 'CHF', 'Canada': 'CAD', 'Australia': 'AUD',
            'New Zealand': 'NZD', 'Norway': 'NOK', 'Brazil': 'BRL',
            'Mexico': 'MXN', 'South Africa': 'ZAR', 'Turkey': 'TRY',
            'India': 'INR', 'China': 'CNY', 'Russia': 'RUB'
        }

        currency = entity_to_currency.get(entity, entity)
        groups = []

        for group_name, currencies in self.currency_correlations.items():
            if currency in currencies:
                groups.append(group_name)

        return groups

    def _get_supply_chain_role(self, entity: str) -> Dict[str, float]:
        """Get entity's role in global supply chains"""
        supply_chain_role = {}

        for commodity, suppliers in self.supply_chain_dependencies.items():
            if entity in suppliers:
                supply_chain_role[commodity] = suppliers[entity]

        return supply_chain_role


class EconomicRelationshipGraph:
    """Graph-based representation of economic relationships with impact propagation"""

    def __init__(self, knowledge_base: EconomicKnowledgeBase):
        self.knowledge_base = knowledge_base
        self.relationships = self._build_relationship_graph()

    def _build_relationship_graph(self) -> Dict[str, Dict[str, EconomicRelationship]]:
        """Build comprehensive relationship graph from knowledge base"""
        graph = {}

        # Add trade relationships
        for source, trade_partners in self.knowledge_base.trade_relationships.items():
            if source not in graph:
                graph[source] = {}

            for target, trade_volume in trade_partners.items():
                relationship = EconomicRelationship(
                    source_entity=source,
                    target_entity=target,
                    relationship_type=RelationshipType.TRADE_PARTNER,
                    strength=trade_volume,
                    direction="bilateral",
                    sectors=["general_trade"],
                    dependency_score=trade_volume,
                    volatility_transmission=trade_volume * 0.8,
                    metadata={'trade_volume_pct': trade_volume}
                )
                graph[source][target] = relationship

        # Add supply chain dependencies
        for commodity, suppliers in self.knowledge_base.supply_chain_dependencies.items():
            for supplier, market_share in suppliers.items():
                if supplier not in graph:
                    graph[supplier] = {}

                # Create relationships with major importers
                major_importers = self._get_major_importers(commodity, supplier)
                for importer in major_importers:
                    relationship = EconomicRelationship(
                        source_entity=supplier,
                        target_entity=importer,
                        relationship_type=RelationshipType.SUPPLY_CHAIN,
                        strength=market_share,
                        direction="unidirectional",
                        sectors=[commodity],
                        dependency_score=market_share * self._get_import_dependency(importer, commodity),
                        volatility_transmission=market_share * 0.9,
                        metadata={'commodity': commodity, 'market_share': market_share}
                    )
                    if importer not in graph[supplier]:
                        graph[supplier][importer] = relationship

        return graph

    def _get_major_importers(self, commodity: str, supplier: str) -> List[str]:
        """Get major importers for a commodity from a supplier"""
        # Simplified mapping - in production, use real trade data
        commodity_importers = {
            'crude_oil': ['Germany', 'Japan', 'China', 'India', 'USA'],
            'natural_gas': ['Germany', 'Japan', 'China', 'Italy', 'Turkey'],
            'wheat': ['Egypt', 'Turkey', 'Bangladesh', 'Nigeria', 'Indonesia'],
            'semiconductors': ['USA', 'China', 'Germany', 'Japan', 'UK'],
            'rare_earth_metals': ['USA', 'Japan', 'Germany', 'South Korea'],
            'lithium': ['China', 'Japan', 'South Korea', 'Germany', 'USA']
        }

        importers = commodity_importers.get(commodity, ['USA', 'China', 'Germany', 'Japan'])
        # Remove supplier from importers list
        return [imp for imp in importers if imp != supplier]

    def _get_import_dependency(self, importer: str, commodity: str) -> float:
        """Get import dependency score for a country-commodity pair"""
        # Simplified dependency scores - in production, use real data
        dependency_matrix = {
            ('Germany', 'natural_gas'): 0.6,
            ('Germany', 'crude_oil'): 0.7,
            ('Japan', 'crude_oil'): 0.9,
            ('Japan', 'natural_gas'): 0.8,
            ('China', 'soybeans'): 0.8,
            ('China', 'iron_ore'): 0.7,
            ('USA', 'rare_earth_metals'): 0.8
        }

        return dependency_matrix.get((importer, commodity), 0.4)

    def get_related_entities(self, entity: str, max_degree: int = 2) -> Dict[str, EconomicRelationship]:
        """Get entities related to the given entity within max_degree hops"""
        related = {}

        if entity in self.relationships:
            # Direct relationships (degree 1)
            for target, relationship in self.relationships[entity].items():
                related[target] = relationship

            # Second-degree relationships if requested
            if max_degree >= 2:
                for target in list(related.keys()):
                    if target in self.relationships:
                        for second_target, second_relationship in self.relationships[target].items():
                            if second_target != entity and second_target not in related:
                                # Create weakened second-degree relationship
                                weakened_relationship = EconomicRelationship(
                                    source_entity=entity,
                                    target_entity=second_target,
                                    relationship_type=second_relationship.relationship_type,
                                    strength=second_relationship.strength * 0.5,  # Weaken by distance
                                    direction=second_relationship.direction,
                                    sectors=second_relationship.sectors,
                                    dependency_score=second_relationship.dependency_score * 0.5,
                                    volatility_transmission=second_relationship.volatility_transmission * 0.3,
                                    metadata={'degree': 2, 'intermediate': target}
                                )
                                related[second_target] = weakened_relationship

        return related

    def calculate_impact_transmission_coefficient(self, source: str, target: str) -> float:
        """Calculate how much impact transmits from source to target"""
        if source in self.relationships and target in self.relationships[source]:
            relationship = self.relationships[source][target]
            return relationship.volatility_transmission
        return 0.0

    def get_systemic_risk_entities(self, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """Identify entities with high systemic risk (many strong connections)"""
        systemic_scores = {}

        for source, targets in self.relationships.items():
            total_exposure = sum(rel.strength for rel in targets.values())
            connection_count = len(targets)
            systemic_score = total_exposure * np.log(1 + connection_count)
            systemic_scores[source] = systemic_score

        # Return entities above threshold, sorted by risk
        high_risk_entities = [
            (entity, score) for entity, score in systemic_scores.items()
            if score >= threshold
        ]

        return sorted(high_risk_entities, key=lambda x: x[1], reverse=True)

    def find_contagion_paths(self, source: str, max_depth: int = 3) -> Dict[str, List[str]]:
        """Find potential contagion paths from source entity"""
        paths = {}

        def dfs_paths(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return

            if current == target and len(path) > 1:
                if target not in paths:
                    paths[target] = []
                paths[target].append(path.copy())
                return

            if current in self.relationships:
                for next_entity, relationship in self.relationships[current].items():
                    if next_entity not in path and relationship.strength > 0.1:  # Significant relationship
                        path.append(next_entity)
                        dfs_paths(next_entity, target, path, depth + 1)
                        path.pop()

        # Find paths to all major economies
        major_entities = ['USA', 'China', 'Germany', 'Japan', 'UK', 'France', 'Italy']

        for target in major_entities:
            if target != source:
                dfs_paths(source, target, [source], 0)

        return paths


# Example usage and testing
if __name__ == "__main__":
    def test_economic_graph():
        """Test the economic knowledge graph"""

        # Initialize knowledge base and graph
        kb = EconomicKnowledgeBase()
        graph = EconomicRelationshipGraph(kb)

        print("=== Economic Knowledge Graph Test ===\n")

        # Test entity context
        print("1. Entity Context for Germany:")
        context = kb.get_entity_context('Germany')
        print(f"Trade Partners: {list(context['trade_partners'].keys())}")
        print(f"Currency Groups: {context['currency_group']}")
        print(f"Supply Chain Role: {context['supply_chain_role']}")

        print("\n2. Economic Relationships for Russia:")
        related = graph.get_related_entities('Russia', max_degree=1)
        for entity, relationship in list(related.items())[:5]:  # Show first 5
            print(f"  {entity}: {relationship.relationship_type.value} (strength: {relationship.strength:.3f})")

        print("\n3. Systemic Risk Entities:")
        risky_entities = graph.get_systemic_risk_entities(threshold=0.5)
        for entity, score in risky_entities[:5]:
            print(f"  {entity}: {score:.3f}")

        print("\n4. Contagion Paths from Russia:")
        contagion_paths = graph.find_contagion_paths('Russia', max_depth=2)
        for target, paths in list(contagion_paths.items())[:3]:
            print(f"  To {target}: {paths[0] if paths else 'No path found'}")

        print("\n5. Impact Transmission Coefficients:")
        test_pairs = [('Russia', 'Germany'), ('China', 'USA'), ('Saudi Arabia', 'Japan')]
        for source, target in test_pairs:
            coeff = graph.calculate_impact_transmission_coefficient(source, target)
            print(f"  {source} → {target}: {coeff:.3f}")

    test_economic_graph()