"""
LLM Provider Abstraction Layer
Supports multiple LLM providers: Mock, Gemini Flash, Claude, etc.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

from config_loader import get_config

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers"""
    MOCK = "mock"
    GEMINI_FLASH = "gemini_flash"
    CLAUDE = "claude"
    # Add more providers as needed


class BaseLLMClient(ABC):
    """Base class for all LLM clients"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name
        config = get_config()
        self.temperature = config.model_config.temperature
        self.max_tokens = config.model_config.max_tokens

    @abstractmethod
    async def analyze_impact(self, news_headline: str, entity_id: str,
                           entity_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze impact of news on entity

        Returns:
            {
                'probabilities': {
                    'abstain': float,
                    'case_1_minor': float,
                    'case_2_moderate': float,
                    'case_3_major': float
                },
                'reasoning': str,
                'confidence': float,
                'model_used': str
            }
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get human-readable provider name"""
        pass


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing"""

    def __init__(self, model_name: str = "mock-llm-v1"):
        super().__init__(model_name)
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
        """Mock LLM analysis"""
        await asyncio.sleep(0.1)  # Simulate API call

        news_type = self._classify_news_type(news_headline)
        template = self.response_templates.get(news_type, self.response_templates['default'])

        probabilities = template['probabilities'].copy()

        # Add entity-specific variation
        if 'safe_haven' in entity_context.get('currency_group', []):
            if news_type == 'conflict':
                probabilities['case_3_major'] += 0.1
                probabilities['abstain'] -= 0.1

        # Normalize
        total = sum(probabilities.values())
        probabilities = {k: v/total for k, v in probabilities.items()}

        return {
            'probabilities': probabilities,
            'reasoning': template['reasoning'] + f" (Entity: {entity_id})",
            'confidence': 0.8,
            'model_used': f"Mock LLM ({self.model_name})"
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

    def get_provider_name(self) -> str:
        return "Mock LLM (Testing)"


class GeminiFlashClient(BaseLLMClient):
    """Google Gemini Flash client"""

    def __init__(self, model_name: str = "gemini-flash-lite-latest",
                 project_id: str = None, region: str = None):
        super().__init__(model_name)
        config = get_config()
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region or config.model_config.google_cloud_region
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup Google Cloud credentials"""
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.info(f"Using Google credentials from: {credentials_path}")

        if not self.project_id:
            logger.warning("No Google Cloud project ID found. Set GOOGLE_CLOUD_PROJECT environment variable")

    async def analyze_impact(self, news_headline: str, entity_id: str,
                           entity_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using Gemini Flash"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project_id, location=self.region)
            model = GenerativeModel(self.model_name)

            prompt = self._build_analysis_prompt(news_headline, entity_id, entity_context)

            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "top_p": 0.8,
                "top_k": 40
            }

            response = model.generate_content(prompt, generation_config=generation_config)

            if response.text:
                return self._parse_response(response.text)
            else:
                raise Exception("No response text from Gemini")

        except ImportError:
            logger.error("Google Cloud AI Platform not installed. Install with: pip install google-cloud-aiplatform")
            raise
        except Exception as e:
            logger.error(f"Error calling Gemini Flash: {e}")
            raise

    def _build_analysis_prompt(self, news_headline: str, entity_id: str,
                             entity_context: Dict[str, Any]) -> str:
        """Build structured prompt for Gemini"""
        return f"""
Analyze the financial impact of this news headline on the specified entity:

NEWS: "{news_headline}"
ENTITY: {entity_id}

ENTITY CONTEXT:
- Trade Partners: {entity_context.get('trade_partners', {})}
- Economic Indicators: {entity_context.get('economic_indicators', {})}
- Currency Groups: {entity_context.get('currency_group', [])}

REQUIRED OUTPUT (JSON format):
{{
    "probabilities": {{
        "abstain": [0-1],
        "case_1_minor": [0-1],
        "case_2_moderate": [0-1],
        "case_3_major": [0-1]
    }},
    "reasoning": "Detailed explanation",
    "confidence": [0-1]
}}

Focus on economic fundamentals and logical cause-effect relationships.
        """

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response"""
        import re
        import json

        try:
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))

                if 'probabilities' in parsed:
                    probs = parsed['probabilities']
                    total = sum(probs.values())
                    if total > 0:
                        for field in probs.keys():
                            probs[field] = probs[field] / total

                    return {
                        'probabilities': probs,
                        'reasoning': parsed.get('reasoning', 'Impact analysis completed'),
                        'confidence': parsed.get('confidence', 0.7),
                        'model_used': f"Google Gemini Flash ({self.model_name})"
                    }
        except Exception as e:
            logger.warning(f"Error parsing Gemini response: {e}")

        # Fallback
        return {
            'probabilities': {'abstain': 0.2, 'case_1_minor': 0.3, 'case_2_moderate': 0.3, 'case_3_major': 0.2},
            'reasoning': f"Fallback analysis: {response_text[:200]}",
            'confidence': 0.5,
            'model_used': f"Google Gemini Flash ({self.model_name}) - Fallback"
        }

    def get_provider_name(self) -> str:
        return "Google Gemini Flash"


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude client"""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", api_key: str = None):
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            logger.warning("No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable")

    async def analyze_impact(self, news_headline: str, entity_id: str,
                           entity_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using Claude"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = self._build_analysis_prompt(news_headline, entity_id, entity_context)

            message = client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            return self._parse_response(response_text)

        except ImportError:
            logger.error("Anthropic SDK not installed. Install with: pip install anthropic")
            raise
        except Exception as e:
            logger.error(f"Error calling Claude: {e}")
            raise

    def _build_analysis_prompt(self, news_headline: str, entity_id: str,
                             entity_context: Dict[str, Any]) -> str:
        """Build structured prompt for Claude"""
        return f"""Analyze the financial impact of this news headline on the specified currency:

NEWS: "{news_headline}"
ENTITY: {entity_id}

ENTITY CONTEXT:
- Trade Partners: {entity_context.get('trade_partners', {})}
- Currency Groups: {entity_context.get('currency_group', [])}

Provide your analysis in JSON format:
{{
    "probabilities": {{
        "abstain": [0-1],
        "case_1_minor": [0-1],
        "case_2_moderate": [0-1],
        "case_3_major": [0-1]
    }},
    "reasoning": "Clear explanation of the impact assessment",
    "confidence": [0-1]
}}

Focus on direct and indirect economic impacts."""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude response"""
        import re
        import json

        try:
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))

                if 'probabilities' in parsed:
                    probs = parsed['probabilities']
                    total = sum(probs.values())
                    if total > 0:
                        for field in probs.keys():
                            probs[field] = probs[field] / total

                    return {
                        'probabilities': probs,
                        'reasoning': parsed.get('reasoning', 'Impact analysis completed'),
                        'confidence': parsed.get('confidence', 0.7),
                        'model_used': f"Anthropic Claude ({self.model_name})"
                    }
        except Exception as e:
            logger.warning(f"Error parsing Claude response: {e}")

        # Fallback
        return {
            'probabilities': {'abstain': 0.2, 'case_1_minor': 0.3, 'case_2_moderate': 0.3, 'case_3_major': 0.2},
            'reasoning': f"Fallback analysis: {response_text[:200]}",
            'confidence': 0.5,
            'model_used': f"Anthropic Claude ({self.model_name}) - Fallback"
        }

    def get_provider_name(self) -> str:
        return "Anthropic Claude"


class LLMClientFactory:
    """Factory for creating LLM clients"""

    @staticmethod
    def create_client(provider: LLMProvider, **kwargs) -> BaseLLMClient:
        """Create an LLM client based on provider"""

        if provider == LLMProvider.MOCK:
            return MockLLMClient(**kwargs)

        elif provider == LLMProvider.GEMINI_FLASH:
            return GeminiFlashClient(**kwargs)

        elif provider == LLMProvider.CLAUDE:
            return ClaudeClient(**kwargs)

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @staticmethod
    def get_available_providers() -> Dict[str, str]:
        """Get list of available providers with descriptions"""
        return {
            LLMProvider.MOCK: "Mock LLM (Fast testing, no API required)",
            LLMProvider.GEMINI_FLASH: "Google Gemini Flash (Requires Google Cloud)",
            LLMProvider.CLAUDE: "Anthropic Claude (Requires Anthropic API key)"
        }
