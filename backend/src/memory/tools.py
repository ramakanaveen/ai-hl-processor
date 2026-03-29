from langchain.tools import BaseTool
from pydantic import Field
from typing import Optional
from src.memory.file_store import FileSystemMemory
from src.memory.pattern_tracker import PatternTracker


class SearchSimilarHeadlinesTool(BaseTool):
    """Tool for agent to search similar past headlines"""

    name: str = "search_similar_headlines"
    description: str = """
    Search for similar headlines that were analyzed in the past.
    Input: A headline text to search for.
    Output: List of similar past headlines with their impact assessments.
    Use this to learn from past analyses before making a new assessment.
    """

    memory: FileSystemMemory = Field(exclude=True)

    def _run(self, headline: str) -> str:
        """Synchronous version"""
        similar = self.memory.search_similar_headlines(headline, limit=3)

        if not similar:
            return "No similar headlines found in memory."

        result = "Similar past headlines:\n\n"
        for i, analysis in enumerate(similar, 1):
            result += f"{i}. \"{analysis.headline}\"\n"
            result += f"   Impacted: {', '.join(e.currency for e in analysis.impacted_entities)}\n"
            for entity in analysis.impacted_entities:
                result += f"   - {entity.currency}: {entity.confidence:.2f} confidence\n"
            result += "\n"

        return result

    async def _arun(self, headline: str) -> str:
        """Async version"""
        return self._run(headline)


class GetCurrencyHistoryTool(BaseTool):
    """Tool for agent to get historical impact patterns for a currency"""

    name: str = "get_currency_history"
    description: str = """
    Get recent historical impact patterns for a specific currency.
    Input: Currency code (e.g., "GBP", "USD", "EUR")
    Output: Recent headlines that impacted this currency with confidence scores.
    Use this to understand how this currency has been impacted recently.
    """

    memory: FileSystemMemory = Field(exclude=True)

    def _run(self, currency: str) -> str:
        """Synchronous version"""
        history = self.memory.get_currency_impact_history(
            currency.upper(),
            days=30
        )

        if not history:
            return f"No recent impacts found for {currency} in the last 30 days."

        result = f"Recent {currency} impacts (last 30 days):\n\n"
        for i, impact in enumerate(history[:5], 1):
            result += f"{i}. \"{impact['headline']}\"\n"
            result += f"   Confidence: {impact['confidence']:.2f}\n"
            result += f"   Reasoning: {impact['reasoning']}\n\n"

        return result

    async def _arun(self, currency: str) -> str:
        """Async version"""
        return self._run(currency)


class GetPatternInsightsTool(BaseTool):
    """Tool for agent to get learned patterns"""

    name: str = "get_pattern_insights"
    description: str = """
    Get learned patterns about which event types impact which currencies.
    Input: A keyword or event type (e.g., "tax", "rates", "trade")
    Output: Historical patterns showing currency impacts for similar events.
    Use this to leverage historical knowledge.
    """

    pattern_tracker: PatternTracker = Field(exclude=True)

    def _run(self, keyword: str) -> str:
        """Synchronous version"""
        patterns = self.pattern_tracker.get_event_currency_patterns()

        keyword_lower = keyword.lower()
        if keyword_lower not in patterns:
            return f"No historical patterns found for keyword '{keyword}'"

        currency_patterns = patterns[keyword_lower]
        result = f"Historical patterns for '{keyword}':\n\n"

        for currency, avg_conf in sorted(
            currency_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            result += f"  {currency}: {avg_conf:.2f} average confidence\n"

        return result

    async def _arun(self, keyword: str) -> str:
        """Async version"""
        return self._run(keyword)


def create_memory_tools(memory: FileSystemMemory) -> list:
    """Factory function to create all memory tools"""
    pattern_tracker = PatternTracker(memory)

    return [
        SearchSimilarHeadlinesTool(memory=memory),
        GetCurrencyHistoryTool(memory=memory),
        GetPatternInsightsTool(pattern_tracker=pattern_tracker)
    ]
