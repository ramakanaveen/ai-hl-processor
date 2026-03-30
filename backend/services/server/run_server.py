#!/usr/bin/env python3
"""
Combined Headline Analysis + SSE Server — Entry Point

Runs the analyzer and SSE/REST server in a single process.

Usage:
    python3 run_server.py --environment dev --port 8080
"""
import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import uvicorn
from src.config.loader import get_config
from src.memory.redis_store import RedisImpactStore
from src.memory.file_store import FileSystemMemory
from src.llm.client_factory import create_analysis_agent
from src.core.analyzer import HeadlineImpactAnalyzer
from services.server.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Headline Impact Server")
    parser.add_argument('--environment', '-e', default='dev',
                        choices=['test', 'dev', 'uat', 'prod'])
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()

    config = get_config(environment=args.environment)
    feed_cfg = config.get_feed_config()
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

    file_store = FileSystemMemory(base_path='memory_store')

    agent = create_analysis_agent(config, file_store, redis_store=redis_store)
    analyzer = HeadlineImpactAnalyzer(agent, file_store, None, config, redis_store=redis_store)

    app = create_app(
        bootstrap_servers=feed_cfg['kafka_bootstrap_servers'],
        input_topic=feed_cfg['kafka_input_topic'],
        output_topic=feed_cfg['kafka_output_topic'],
        consumer_group=feed_cfg['kafka_consumer_group'],
        analyzer=analyzer,
        redis_store=redis_store,
        file_store=file_store,
        environment=args.environment,
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
