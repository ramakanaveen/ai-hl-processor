#!/usr/bin/env python3
"""
Headline Impact Analyzer — Agent-powered with file system memory
"""
import asyncio
import argparse
import json
import logging
from datetime import datetime

from aiokafka import AIOKafkaProducer

from src.core.analyzer import HeadlineImpactAnalyzer
from src.llm.client_factory import create_analysis_agent
from src.memory.file_store import FileSystemMemory
from src.config.loader import get_config
from src.feeds.kafka_adapter import KafkaFeedAdapter

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
    parser.add_argument('--analyze', type=str, help='Analyze a single headline')
    parser.add_argument('--demo', action='store_true', help='Run demo with sample headlines')
    parser.add_argument('--stream', action='store_true', help='Stream from Kafka raw-headlines topic')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    config = get_config(environment=args.environment)
    logger.info(f"Loaded config for environment: {config.environment}")

    memory = FileSystemMemory(base_path='memory_store')
    mem_stats = memory.get_stats()
    logger.info(f"Memory store: {mem_stats['total_analyses']} analyses at memory_store/")

    from src.memory.redis_store import RedisImpactStore
    cache_cfg = config.get_cache_config()
    redis_cfg = config.get_redis_config()
    redis_store = RedisImpactStore(
        host=cache_cfg['redis_host'],
        port=cache_cfg['redis_port'],
        db=cache_cfg['redis_db'],
        ttl_seconds=cache_cfg['cache_ttl_seconds'],
        active_window_minutes=redis_cfg['active_impact_window_minutes'],
        password=redis_cfg['password'],
        ssl=redis_cfg['ssl'],
        ssl_cert_reqs=redis_cfg['ssl_cert_reqs'],
        socket_timeout=redis_cfg['socket_timeout'],
        socket_connect_timeout=redis_cfg['socket_connect_timeout'],
        max_connections=redis_cfg['max_connections'],
    )
    await redis_store.connect()

    agent = create_analysis_agent(config, memory, redis_store=redis_store)
    analyzer = HeadlineImpactAnalyzer(agent, memory, None, config, redis_store=redis_store)

    if args.analyze:
        result = await analyzer.analyze_headline(args.analyze)
        if args.json:
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            analyzer._print_result(result)

    elif args.demo:
        demo_headlines = [
            "Rachel Reeves announces major tax increase on UK businesses",
            "Federal Reserve raises interest rates by 75 basis points",
            "ECB announces emergency €750 billion bond buying program",
            "Bank of Japan intervenes in currency markets for first time since 1998",
            "China devalues yuan amid escalating trade tensions with US",
        ]

        print("Demo Mode - Analyzing Sample Headlines\n")
        for headline in demo_headlines:
            result = await analyzer.analyze_headline(headline)
            if args.json:
                print(json.dumps(result.model_dump(), indent=2, default=str))
            else:
                analyzer._print_result(result)

        stats = analyzer.get_stats()
        print(f"\nPerformance Stats:")
        print(f"  Total analyzed: {stats['total_analyzed']}")
        print(f"  Average time:   {stats['average_processing_time_ms']:.1f}ms")
        print(f"  Errors:         {stats['errors']}")
        print(f"\nMemory Stats:")
        print(f"  Total stored:   {stats['memory_stats']['total_analyses']}")

    elif args.stream:
        feed_cfg = config.get_feed_config()
        bootstrap = feed_cfg['kafka_bootstrap_servers']
        input_topic = feed_cfg['kafka_input_topic']
        output_topic = feed_cfg['kafka_output_topic']
        consumer_group = feed_cfg['kafka_consumer_group']

        logger.info("Stream Mode Starting...")
        logger.info(f"  Broker:        {bootstrap}")
        logger.info(f"  Input topic:   {input_topic}")
        logger.info(f"  Output topic:  {output_topic}")
        logger.info(f"  Consumer group:{consumer_group}")
        logger.info(f"  Environment:   {config.environment}")
        logger.info(f"  Model:         {config.model_config.model_name}")

        feed_adapter = KafkaFeedAdapter(
            bootstrap_servers=bootstrap,
            topic=input_topic,
            group_id=consumer_group,
        )

        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
            enable_idempotence=True,
        )
        await producer.start()

        async def publish_result(result):
            message = {
                "type": "analysis_result",
                "timestamp": datetime.now().isoformat(),
                "data": result.model_dump(),
            }
            await producer.send(output_topic, message)
            logger.debug(f"Published result for: {result.headline[:60]}...")

        analyzer.feed_adapter = feed_adapter

        try:
            logger.info("Starting feed processing... (Ctrl+C to stop)")
            await analyzer.process_feed(callback=publish_result)

        except KeyboardInterrupt:
            logger.info("Stream processing stopped by user")
            stats = analyzer.get_stats()
            print(f"\nFinal Stats:")
            print(f"  Total analyzed: {stats['total_analyzed']}")
            print(f"  Average time:   {stats['average_processing_time_ms']:.1f}ms")
            print(f"  Errors:         {stats['errors']}")

        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            raise

        finally:
            await producer.stop()
            await redis_store.close()

    else:
        parser.print_help()
        await redis_store.close()


if __name__ == "__main__":
    asyncio.run(main())
