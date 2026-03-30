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

stop_process "run_server.py" "Combined Server"
stop_process "run_producer.py" "Kafka Producer"

echo ""
echo "========================================="
echo "All services stopped"
echo "========================================="
echo ""
