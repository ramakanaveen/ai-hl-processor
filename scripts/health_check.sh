#!/bin/bash
# Health Check
# Checks the status of all pipeline services

echo "========================================="
echo "Service Health Check"
echo "========================================="
echo ""

# Function to check if process is running
check_process() {
    local pattern=$1
    local name=$2

    if pgrep -f "$pattern" > /dev/null; then
        local pid=$(pgrep -f "$pattern" | head -n 1)
        echo "✓ $name: RUNNING (PID: $pid)"
        return 0
    else
        echo "✗ $name: DOWN"
        return 1
    fi
}

echo "Checking services..."
echo ""

all_running=0

check_process "run_input_server.py" "Input WebSocket Server (port 8765)"
all_running=$((all_running + $?))

check_process "run_output_server.py" "Output WebSocket Server (port 8766)"
all_running=$((all_running + $?))

check_process "run_poller.py" "RSS Feed Poller"
all_running=$((all_running + $?))

check_process "main.py --stream" "Analyzer (stream mode)"
all_running=$((all_running + $?))

check_process "run_writer.py" "File Writer Service"
all_running=$((all_running + $?))

echo ""
echo "========================================="

if [ $all_running -eq 0 ]; then
    echo "Status: All services running ✓"
    echo "========================================="
    echo ""

    # Show recent log entries
    echo "Recent activity (last 5 lines from each log):"
    echo ""

    if [ -f "logs/input_ws.log" ]; then
        echo "Input WebSocket:"
        tail -n 3 logs/input_ws.log | sed 's/^/  /'
        echo ""
    fi

    if [ -f "logs/rss_poller.log" ]; then
        echo "RSS Poller:"
        tail -n 3 logs/rss_poller.log | sed 's/^/  /'
        echo ""
    fi

    if [ -f "logs/analyzer.log" ]; then
        echo "Analyzer:"
        tail -n 3 logs/analyzer.log | sed 's/^/  /'
        echo ""
    fi

    if [ -f "logs/file_writer.log" ]; then
        echo "File Writer:"
        tail -n 3 logs/file_writer.log | sed 's/^/  /'
        echo ""
    fi
else
    echo "Status: Some services not running ✗"
    echo "========================================="
    echo ""
    echo "To start all services: ./scripts/start_all.sh"
fi

echo ""
