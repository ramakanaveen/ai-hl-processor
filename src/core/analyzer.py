import time
import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable
from src.core.models import ImpactAnalysisResult, Headline, CurrencyImpact
from src.memory.file_store import FileSystemMemory

logger = logging.getLogger(__name__)


class HeadlineImpactAnalyzer:
    """
    Agent-powered analyzer with file system memory
    """

    def __init__(
        self,
        agent_executor,  # LangChain AgentExecutor
        memory: FileSystemMemory,
        feed_adapter=None,
        config=None,
        redis_store=None,
    ):
        self.agent = agent_executor
        self.memory = memory
        self.feed_adapter = feed_adapter
        self.config = config
        self.redis_store = redis_store

        # Performance tracking
        self.stats = {
            'total_analyzed': 0,
            'total_processing_time_ms': 0,
            'errors': 0
        }

    async def analyze_headline(self, headline_text: str) -> ImpactAnalysisResult:
        """
        Analyze headline using agent with memory tools

        The agent will:
        1. Search for similar past headlines
        2. Check currency impact history
        3. Use pattern insights
        4. Make informed assessment
        5. Store result in memory
        """
        start_time = time.time()

        try:
            # Invoke agent with headline
            agent_output = await self.agent.ainvoke({
                "input": f"Analyze this headline for currency impact: {headline_text}"
            })

            # Parse agent output
            output_data = agent_output.get('output', {})

            # Convert to CurrencyImpact objects
            impacted_entities = []
            for impact in output_data.get('impacted_currencies', []):
                impacted_entities.append(CurrencyImpact(
                    currency=impact['currency'],
                    confidence=impact['confidence'],
                    reasoning=impact['reasoning']
                ))

            processing_time_ms = (time.time() - start_time) * 1000

            # Update stats
            self.stats['total_analyzed'] += 1
            self.stats['total_processing_time_ms'] += processing_time_ms

            # Create result
            result = ImpactAnalysisResult(
                headline=headline_text,
                timestamp=datetime.now(),
                impacted_entities=impacted_entities,
                processing_time_ms=round(processing_time_ms, 2),
                model_used=self.config.model_config.model_name if self.config else "unknown"
            )

            # Store in memory for future reference
            self.memory.store_analysis(result)
            logger.info(f"Stored analysis in memory: {len(impacted_entities)} entities impacted")

            # Store in Redis cache and impact timeline (best-effort)
            if self.redis_store and await self.redis_store.is_available():
                await self.redis_store.cache_result(result)
                await self.redis_store.store_impact_timeline(result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing headline '{headline_text[:50]}...': {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            self.stats['errors'] += 1

            result = ImpactAnalysisResult(
                headline=headline_text,
                timestamp=datetime.now(),
                impacted_entities=[],
                processing_time_ms=round(processing_time_ms, 2),
                model_used="error",
                error=str(e)
            )

            # Still store even errors for tracking
            self.memory.store_analysis(result)

            return result

    async def process_feed(
        self,
        callback: Optional[Callable[[ImpactAnalysisResult], Awaitable[None]]] = None
    ):
        """Process continuous headline feed"""
        if not self.feed_adapter:
            raise RuntimeError("No feed adapter configured")

        try:
            await self.feed_adapter.connect()
            logger.info("Started processing feed with memory-enabled agent...")

            async for headline in self.feed_adapter.stream_headlines():
                result = await self.analyze_headline(headline.text)

                if callback:
                    await callback(result)
                else:
                    self._print_result(result)

        except KeyboardInterrupt:
            logger.info("Feed processing interrupted")
        finally:
            await self.feed_adapter.disconnect()

    def _print_result(self, result: ImpactAnalysisResult):
        """Print result to console"""
        print(f"\n{'='*80}")
        print(f"📰 {result.headline}")
        print(f"⏱️  {result.processing_time_ms:.0f}ms | {result.timestamp.strftime('%H:%M:%S')}")

        if result.error:
            print(f"❌ Error: {result.error}")
        elif result.impacted_entities:
            print(f"\n💱 Impacted Currencies ({len(result.impacted_entities)}):")
            for impact in result.impacted_entities:
                conf_bar = '█' * int(impact.confidence * 10)
                print(f"  {impact.currency.value}: {conf_bar} {impact.confidence:.2f}")
                print(f"     → {impact.reasoning}")
        else:
            print("ℹ️  No significant currency impacts detected")

    def get_stats(self) -> dict:
        """Get performance statistics"""
        memory_stats = self.memory.get_stats()

        avg_time = (
            self.stats['total_processing_time_ms'] / self.stats['total_analyzed']
            if self.stats['total_analyzed'] > 0 else 0
        )

        return {
            **self.stats,
            'average_processing_time_ms': round(avg_time, 2),
            'memory_stats': memory_stats
        }
