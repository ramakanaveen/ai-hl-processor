#!/usr/bin/env python3
"""
Kafka Headline Producer

Reads headlines from a configured source and publishes to the raw-headlines topic.

Usage:
    # From a CSV file (rate-limited to 1 headline/sec)
    python3 run_producer.py --source file --file data/headlines.csv

    # From KDB+ (polls every 60s)
    python3 run_producer.py --source kdb --environment uat
"""
import asyncio
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.config.loader import get_config
from src.sources.file_source import FileSource
from src.sources.kdb_source import KDBSource
from services.kafka_producer.producer_service import KafkaProducerService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Kafka headline producer")
    parser.add_argument('--source', choices=['file', 'kdb'], required=True,
                        help='Headline source type')
    parser.add_argument('--file', type=str,
                        help='Path to CSV file (required when --source=file)')
    parser.add_argument('--environment', '-e', default='dev',
                        choices=['test', 'dev', 'uat', 'prod'])
    args = parser.parse_args()

    config = get_config(environment=args.environment)
    feed_cfg = config.get_feed_config()

    bootstrap = feed_cfg['kafka_bootstrap_servers']
    input_topic = feed_cfg['kafka_input_topic']

    if args.source == 'file':
        if not args.file:
            parser.error('--file is required when --source=file')
        source = FileSource(
            file_path=args.file,
            rate_limit_per_second=feed_cfg.get('file_source_rate_per_second', 1.0),
        )

    elif args.source == 'kdb':
        kdb_cfg = config.get_kdb_config()
        source = KDBSource(
            host=kdb_cfg['host'],
            port=kdb_cfg['port'],
            query=kdb_cfg['query'],
            poll_interval_seconds=kdb_cfg['poll_interval_seconds'],
            username=kdb_cfg.get('username'),
            password=kdb_cfg.get('password'),
        )

    service = KafkaProducerService(
        source=source,
        bootstrap_servers=bootstrap,
        topic=input_topic,
    )

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")


if __name__ == '__main__':
    asyncio.run(main())
