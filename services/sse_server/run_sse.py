#!/usr/bin/env python3
"""
SSE Server Entry Point

Usage:
    python3 run_sse.py --environment uat --port 8080
"""
import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import uvicorn
from src.config.loader import get_config
from services.sse_server.sse_server import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Headline Impact SSE Server")
    parser.add_argument('--environment', '-e', default='dev',
                        choices=['test', 'dev', 'uat', 'prod'])
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()

    config = get_config(environment=args.environment)
    feed_cfg = config.get_feed_config()

    app = create_app(
        bootstrap_servers=feed_cfg['kafka_bootstrap_servers'],
        topic=feed_cfg['kafka_output_topic'],
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
