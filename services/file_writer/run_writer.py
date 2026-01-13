#!/usr/bin/env python3
"""
Run File Writer Service
Entry point for starting the file writer service
"""
import asyncio
import logging
from file_writer_service import FileWriterService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Start the file writer service"""
    try:
        writer = FileWriterService()
        logger.info("File Writer Service starting...")
        await writer.run()

    except KeyboardInterrupt:
        logger.info("Service stopped by user")

        # Print final stats
        stats = writer.get_stats()
        logger.info(f"Final stats: {stats['total_results_written']} results written, {stats['errors']} errors")

    except Exception as e:
        logger.error(f"Service error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
