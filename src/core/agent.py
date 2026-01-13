
from langchain_core.agents import AgentFinish
from src.memory.file_store import FileSystemMemory
from src.memory.tools import create_memory_tools
import logging

logger = logging.getLogger(__name__)


def create_impact_analysis_agent(config, memory: FileSystemMemory):
    """
    Create LangChain agent for headline impact analysis with memory
    Uses Gemini Flash via Vertex AI with memory context enrichment
    """
    from langchain_google_vertexai import ChatVertexAI
    import os
    import json
    import warnings

    # Suppress deprecation warnings for ChatVertexAI
    # Note: We use Vertex AI (not Developer API) so ChatVertexAI is correct despite deprecation warning
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='langchain_google_vertexai')
    from langchain_core._api import LangChainDeprecationWarning
    warnings.filterwarnings('ignore', category=LangChainDeprecationWarning)

    # Set up Google Application Credentials
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS from GOOGLE_CREDENTIALS_PATH")

    # Initialize Gemini via Vertex AI
    llm = ChatVertexAI(
        model_name=config.model_config.model_name,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_LOCATION", "us-central1"),
        temperature=config.model_config.temperature,
        max_output_tokens=config.model_config.max_tokens,
    )

    class GeminiAgentExecutor:
        """Custom agent executor that enriches prompts with memory context"""

        def __init__(self, llm, memory, config):
            self.llm = llm
            self.memory = memory
            self.config = config

        async def ainvoke(self, inputs: dict) -> dict:
            """Invoke with memory-enriched prompt"""
            headline = inputs['input'].replace("Analyze this headline for currency impact: ", "")

            # Search for similar headlines in memory
            similar = self.memory.search_similar_headlines(headline, limit=3, similarity_threshold=0.4)

            # Build memory context
            memory_context = ""
            if similar:
                memory_context = "\n\nRELEVANT PAST ANALYSES:\n"
                for i, analysis in enumerate(similar, 1):
                    memory_context += f"\n{i}. \"{analysis.headline}\"\n"
                    memory_context += f"   Impacted: {', '.join(e.currency for e in analysis.impacted_entities)}\n"
                    for entity in analysis.impacted_entities:
                        memory_context += f"   - {entity.currency}: {entity.confidence:.2f} confidence - {entity.reasoning}\n"

            # Build structured prompt
            system_prompt = """You are an expert financial analyst specializing in currency markets and foreign exchange (FX) trading.

Your task is to analyze news headlines and determine which currencies will be impacted by the news event.

Consider these factors:
1. Direct mentions of countries, central banks, or currencies
2. Economic relationships and trade dependencies
3. Market sentiment and safe-haven flows
4. Central bank policy implications
5. Geopolitical risk factors

IMPORTANT: Return your response as valid JSON with this exact structure:
{
  "impacted_currencies": [
    {
      "currency": "GBP",
      "confidence": 0.85,
      "reasoning": "UK Chancellor fiscal policy directly impacts British pound"
    }
  ]
}

Supported currencies: USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD, CNY
Only include currencies with confidence >= 0.5. If no clear impact, return empty array."""

            user_prompt = f"""Analyze the following news headline for currency impact:

HEADLINE: "{headline}"{memory_context}

Provide your analysis as JSON with impacted_currencies array."""

            # Call Gemini
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response
            try:
                response_text = response.content

                # Extract JSON from response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                # Try to find JSON object
                if "{" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    response_text = response_text[json_start:json_end]

                result = json.loads(response_text)

                # Validate and normalize
                impacted = result.get("impacted_currencies", [])

                # Ensure all required fields
                normalized = []
                for impact in impacted:
                    if isinstance(impact, dict) and "currency" in impact:
                        normalized.append({
                            "currency": impact["currency"],
                            "confidence": float(impact.get("confidence", 0.5)),
                            "reasoning": impact.get("reasoning", "No reasoning provided")
                        })

                return {
                    "output": {
                        "impacted_currencies": normalized
                    }
                }

            except Exception as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                logger.debug(f"Raw response: {response.content}")

                # Fallback: return empty result
                return {
                    "output": {
                        "impacted_currencies": []
                    }
                }

    return GeminiAgentExecutor(llm, memory, config)


def create_mock_agent(memory: FileSystemMemory):
    """
    Create mock agent for test/dev environments
    Simple execution without actual LLM calls
    """
    def mock_agent_logic(inputs: dict) -> AgentFinish:
        """Mock agent that does simple keyword matching"""
        headline = inputs['input'].lower()

        impacts = []

        # Simple keyword matching
        if 'uk' in headline or 'britain' in headline or 'reeves' in headline:
            impacts.append({
                'currency': 'GBP',
                'confidence': 0.85,
                'reasoning': 'Mock: UK-related keywords detected'
            })

        if 'fed' in headline or 'us' in headline or 'powell' in headline or 'federal' in headline:
            impacts.append({
                'currency': 'USD',
                'confidence': 0.90,
                'reasoning': 'Mock: US/Fed-related keywords detected'
            })

        if 'ecb' in headline or 'europe' in headline or 'eu' in headline or 'european' in headline:
            impacts.append({
                'currency': 'EUR',
                'confidence': 0.85,
                'reasoning': 'Mock: EU/ECB-related keywords detected'
            })

        if 'japan' in headline or 'boj' in headline or 'yen' in headline:
            impacts.append({
                'currency': 'JPY',
                'confidence': 0.80,
                'reasoning': 'Mock: Japan/BOJ-related keywords detected'
            })

        if 'china' in headline or 'yuan' in headline or 'pboc' in headline:
            impacts.append({
                'currency': 'CNY',
                'confidence': 0.80,
                'reasoning': 'Mock: China-related keywords detected'
            })

        # Return as AgentFinish with structured output
        return AgentFinish(
            return_values={'output': {'impacted_currencies': impacts}},
            log="Mock agent execution completed"
        )

    # Create simple mock executor
    class MockAgentExecutor:
        def __init__(self, agent_func):
            self.agent_func = agent_func

        async def ainvoke(self, inputs: dict) -> dict:
            result = self.agent_func(inputs)
            return result.return_values

    return MockAgentExecutor(mock_agent_logic)
