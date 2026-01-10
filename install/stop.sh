#!/bin/bash
# Stop script for Simple Uptime Monitor (non-systemd environments)

INSTALL_DIR="/home/jack/Simple-Uptime-Monitor"
PID_FILE="$INSTALL_DIR/data/uptime-monitor.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Simple Uptime Monitor is not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null 2>&1; then
    echo "Stopping Simple Uptime Monitor (PID: $PID)..."
    kill $PID

    # Wait for process to stop
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        echo "Process didn't stop gracefully, forcing..."
        kill -9 $PID
    fi

    rm "$PID_FILE"
    echo "Simple Uptime Monitor stopped"
else
    echo "Process not running (stale PID file), cleaning up..."
    rm "$PID_FILE"
fi
