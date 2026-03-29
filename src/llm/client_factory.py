from src.core.agent import create_impact_analysis_agent, create_mock_agent
from src.memory.file_store import FileSystemMemory
import logging

logger = logging.getLogger(__name__)


def create_analysis_agent(config, memory: FileSystemMemory, redis_store=None):
    """
    Factory function to create appropriate agent based on environment

    Args:
        config: System configuration
        memory: FileSystemMemory instance
        redis_store: Optional RedisImpactStore for headline cache and impact graph

    Returns:
        AgentExecutor that processes headlines with memory tools
    """
    if config.model_config.use_mock_llm:
        logger.info("Using mock agent (test/dev environment)")
        return create_mock_agent(memory, redis_store=redis_store)
    else:
        logger.info(f"Using Gemini Flash agent with memory (environment: {config.environment})")
        return create_impact_analysis_agent(config, memory, redis_store=redis_store)
