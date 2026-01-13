#!/bin/bash
# Stop All Services
# Stops all running pipeline services

echo "========================================="
echo "Stopping AI Headline Processor Pipeline"
echo "========================================="
echo ""

# Function to stop process by pattern
stop_process() {
    local pattern=$1
    local name=$2

    if pgrep -f "$pattern" > /dev/null; then
        pkill -f "$pattern"
        echo "✓ Stopped $name"
    else
        echo "ℹ $name not running"
    fi
}

echo "Stopping services..."

stop_process "run_input_server.py" "Input WebSocket Server"
stop_process "run_output_server.py" "Output WebSocket Server"
stop_process "run_poller.py" "RSS Feed Poller"
stop_process "main.py --stream" "Analyzer (stream mode)"
stop_process "run_writer.py" "File Writer Service"

echo ""
echo "========================================="
echo "All services stopped"
echo "========================================="
echo ""
