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

check_process "run_server.py" "Combined Server (port 8080)"
all_running=$((all_running + $?))

check_process "run_producer.py" "Kafka Producer"
all_running=$((all_running + $?))

echo ""
echo "========================================="

if [ $all_running -eq 0 ]; then
    echo "Status: All services running ✓"
    echo "========================================="
    echo ""

    # HTTP health check on SSE server
    echo "Combined Server health endpoint:"
    curl -s http://localhost:8080/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (not reachable)"
    echo ""

    # Show recent log entries
    echo "Recent activity (last 3 lines from each log):"
    echo ""

    for log in logs/server.log logs/producer.log; do
        if [ -f "$log" ]; then
            echo "$(basename $log .log):"
            tail -n 3 "$log" | sed 's/^/  /'
            echo ""
        fi
    done
else
    echo "Status: Some services not running ✗"
    echo "========================================="
    echo ""
    echo "To start all services: ./scripts/start_all.sh"
fi

echo ""
