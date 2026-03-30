#!/bin/bash
# Start All Services — Kafka-based pipeline
#
# Requires: Docker running (for Kafka), Python 3.11+, pip dependencies installed
#
# Usage: ./scripts/start_all.sh [environment] [csv_file]
#   environment  test|dev|uat|prod  (default: uat)
#   csv_file     path to headlines CSV for file source  (default: none, uses KDB)

set -e

ENV=${1:-uat}
CSV_FILE=${2:-}

echo "========================================="
echo " AI Headline Processor Pipeline"
echo " Environment: $ENV"
echo "========================================="
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"; exit 1
fi
if ! command -v docker &> /dev/null; then
    echo "Error: docker not found — required for Kafka"; exit 1
fi

cd "$(dirname "$0")/.."
mkdir -p logs

echo "1. Starting Kafka (docker compose)..."
docker compose up -d
echo "   Waiting for Kafka to be ready..."
sleep 8
echo "   Done"
echo ""

echo "2. Starting Server (port 8080)..."
cd services/server
python3 run_server.py --environment "$ENV" --port 8080 > ../../logs/server.log 2>&1 &
SERVER_PID=$!
echo "   Started (PID: $SERVER_PID)"
cd ../..
sleep 2

echo "4. Starting Kafka Producer..."
if [ -n "$CSV_FILE" ]; then
    echo "   Source: file ($CSV_FILE)"
    cd services/kafka_producer
    python3 run_producer.py --source file --file "../../$CSV_FILE" --environment "$ENV" > ../../logs/producer.log 2>&1 &
    PRODUCER_PID=$!
    cd ../..
else
    echo "   Source: kdb"
    cd services/kafka_producer
    python3 run_producer.py --source kdb --environment "$ENV" > ../../logs/producer.log 2>&1 &
    PRODUCER_PID=$!
    cd ../..
fi
echo "   Started (PID: $PRODUCER_PID)"

echo ""
echo "========================================="
echo " All services started"
echo "========================================="
echo ""
echo " Process IDs:"
echo "   Server:      $SERVER_PID"
echo "   Producer:    $PRODUCER_PID"
echo ""
echo " Endpoints:"
echo "   SSE stream:  http://localhost:8080/events"
echo "   Health:      http://localhost:8080/health"
echo ""
echo " Logs:  ./logs/"
echo " Stop:  ./scripts/stop_all.sh"
echo ""
