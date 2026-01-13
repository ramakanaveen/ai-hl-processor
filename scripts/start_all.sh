#!/bin/bash
# Start All Services
# Starts the complete RSS-to-WebSocket pipeline

set -e

echo "========================================="
echo "Starting AI Headline Processor Pipeline"
echo "========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Change to project root
cd "$(dirname "$0")/.."

echo "1. Starting Input WebSocket Server (port 8765)..."
cd services/websocket_servers
python3 run_input_server.py > ../../logs/input_ws.log 2>&1 &
INPUT_WS_PID=$!
echo "   ✓ Started (PID: $INPUT_WS_PID)"
cd ../..
sleep 1

echo "2. Starting Output WebSocket Server (port 8766)..."
cd services/websocket_servers
python3 run_output_server.py > ../../logs/output_ws.log 2>&1 &
OUTPUT_WS_PID=$!
echo "   ✓ Started (PID: $OUTPUT_WS_PID)"
cd ../..
sleep 1

echo "3. Starting RSS Feed Poller..."
cd services/rss_poller
python3 run_poller.py > ../../logs/rss_poller.log 2>&1 &
RSS_POLLER_PID=$!
echo "   ✓ Started (PID: $RSS_POLLER_PID)"
cd ../..
sleep 2

echo "4. Starting Analyzer in Stream Mode..."
python3 main.py --stream --environment uat > logs/analyzer.log 2>&1 &
ANALYZER_PID=$!
echo "   ✓ Started (PID: $ANALYZER_PID)"
sleep 2

echo "5. Starting File Writer Service..."
cd services/file_writer
python3 run_writer.py > ../../logs/file_writer.log 2>&1 &
FILE_WRITER_PID=$!
echo "   ✓ Started (PID: $FILE_WRITER_PID)"
cd ../..

echo ""
echo "========================================="
echo "All services started successfully!"
echo "========================================="
echo ""
echo "Process IDs:"
echo "  Input WebSocket:  $INPUT_WS_PID"
echo "  Output WebSocket: $OUTPUT_WS_PID"
echo "  RSS Poller:       $RSS_POLLER_PID"
echo "  Analyzer:         $ANALYZER_PID"
echo "  File Writer:      $FILE_WRITER_PID"
echo ""
echo "Logs directory: ./logs/"
echo ""
echo "To check status: ./scripts/health_check.sh"
echo "To stop all:     ./scripts/stop_all.sh"
echo ""
