#!/bin/bash
# Startup script for Simple Uptime Monitor (non-systemd environments)

INSTALL_DIR="/home/jack/Simple-Uptime-Monitor"
VENV_DIR="$INSTALL_DIR/venv"
LOG_FILE="$INSTALL_DIR/data/uptime-monitor.log"

cd "$INSTALL_DIR"

# Check if already running
if [ -f "$INSTALL_DIR/data/uptime-monitor.pid" ]; then
    PID=$(cat "$INSTALL_DIR/data/uptime-monitor.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Simple Uptime Monitor is already running (PID: $PID)"
        exit 0
    else
        # Stale PID file, remove it
        rm "$INSTALL_DIR/data/uptime-monitor.pid"
    fi
fi

# Start the service in background
echo "Starting Simple Uptime Monitor..."
source "$VENV_DIR/bin/activate"
nohup python -m uptime_monitor.main >> "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$INSTALL_DIR/data/uptime-monitor.pid"

echo "Simple Uptime Monitor started (PID: $PID)"
echo "Web dashboard: http://localhost:5000"
echo "Logs: $LOG_FILE"
