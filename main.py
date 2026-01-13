#!/usr/bin/env python3
"""
Headline Impact Analyzer - Agent-powered with file system memory
"""
import asyncio
import argparse
import json
import logging
import websockets
from datetime import datetime
from src.core.analyzer import HeadlineImpactAnalyzer
from src.llm.client_factory import create_analysis_agent
from src.memory.file_store import FileSystemMemory
from src.config.loader import get_config
from src.feeds.websocket_adapter import WebSocketFeedAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="Analyze financial headlines for currency impact using LangChain agent"
    )
    parser.add_argument(
        '--environment', '-e',
        choices=['test', 'dev', 'uat', 'prod'],
        default='test',
        help='Environment (determines mock vs real LLM)'
    )
    parser.add_argument(
        '--analyze',
        type=str,
        help='Analyze single headline (one-off mode)'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo with sample headlines'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--memory-path',
        type=str,
        default='memory_store',
        help='Path to file system memory storage'
    )
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Stream and process continuous feed from WebSocket'
    )
    parser.add_argument(
        '--input-ws',
        type=str,
        help='Input WebSocket URL (overrides config)'
    )
    parser.add_argument(
        '--output-ws',
        type=str,
        help='Output WebSocket URL (overrides config)'
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(environment=args.environment)
    logger.info(f"Loaded config for environment: {config.environment}")

    # Initialize file system memory
    memory = FileSystemMemory(base_path=args.memory_path)
    logger.info(f"Initialized memory store at: {args.memory_path}")

    mem_stats = memory.get_stats()
    logger.info(f"Memory stats: {mem_stats['total_analyses']} analyses stored")

    # Create LangChain agent (with memory tools)
    agent = create_analysis_agent(config, memory)

    # Create analyzer
    analyzer = HeadlineImpactAnalyzer(agent, memory, None, config)

    # Execute based on mode
    if args.analyze:
        # Single headline analysis
        result = await analyzer.analyze_headline(args.analyze)
        if args.json:
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            analyzer._print_result(result)

    elif args.demo:
        # Demo mode with sample headlines
        demo_headlines = [
            "Rachel Reeves announces major tax increase on UK businesses",
            "Federal Reserve raises interest rates by 75 basis points",
            "ECB announces emergency €750 billion bond buying program",
            "Bank of Japan intervenes in currency markets for first time since 1998",
            "China devalues yuan amid escalating trade tensions with US"
        ]

        print("🎬 Demo Mode - Analyzing Sample Headlines\n")

        for headline in demo_headlines:
            result = await analyzer.analyze_headline(headline)
            if args.json:
                print(json.dumps(result.model_dump(), indent=2, default=str))
            else:
                analyzer._print_result(result)

        # Print stats
        stats = analyzer.get_stats()
        print(f"\n📊 Performance Stats:")
        print(f"   Total analyzed: {stats['total_analyzed']}")
        print(f"   Average time: {stats['average_processing_time_ms']:.1f}ms")
        print(f"   Errors: {stats['errors']}")
        print(f"\n💾 Memory Stats:")
        print(f"   Total analyses stored: {stats['memory_stats']['total_analyses']}")
        print(f"   Storage path: {stats['memory_stats']['storage_path']}")

    elif args.stream:
        # Stream mode - process continuous feed from WebSocket
        # Get WebSocket URLs from args or config
        feed_config = config.get_feed_config()
        input_ws_url = args.input_ws or feed_config.get('input_websocket_url', 'ws://localhost:8765')
        output_ws_url = args.output_ws or feed_config.get('output_websocket_url', 'ws://localhost:8766')

        logger.info("🌊 Stream Mode Starting...")
        logger.info(f"   Input WebSocket: {input_ws_url}")
        logger.info(f"   Output WebSocket: {output_ws_url}")
        logger.info(f"   Environment: {config.environment}")
        logger.info(f"   Model: {config.model_config.model_name}")

        # Create WebSocket feed adapter
        feed_adapter = WebSocketFeedAdapter(input_ws_url)

        # Create output WebSocket publisher
        async def publish_result(result):
            """Publish analysis result to output WebSocket"""
            try:
                async with websockets.connect(output_ws_url) as websocket:
                    message = {
                        "type": "analysis_result",
                        "timestamp": datetime.now().isoformat(),
                        "data": result.model_dump()
                    }
                    await websocket.send(json.dumps(message, default=str))
                    logger.debug(f"Published result for: {result.headline[:50]}...")

            except websockets.exceptions.WebSocketException as e:
                logger.error(f"Failed to publish result to output WebSocket: {e}")
            except Exception as e:
                logger.error(f"Error publishing result: {e}")

        # Update analyzer with feed adapter
        analyzer.feed_adapter = feed_adapter

        # Start processing feed
        try:
            logger.info("✓ Starting feed processing... (Press Ctrl+C to stop)")
            await analyzer.process_feed(callback=publish_result)

        except KeyboardInterrupt:
            logger.info("\n⏹  Stream processing stopped by user")

            # Print final stats
            stats = analyzer.get_stats()
            print(f"\n📊 Performance Stats:")
            print(f"   Total analyzed: {stats['total_analyzed']}")
            print(f"   Average time: {stats['average_processing_time_ms']:.1f}ms")
            print(f"   Errors: {stats['errors']}")
            print(f"\n💾 Memory Stats:")
            print(f"   Total analyses stored: {stats['memory_stats']['total_analyses']}")

        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            raise

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
