#!/bin/bash
# Installation script for Simple Uptime Monitor
# Compatible with: WSL, Ubuntu, Docker containers

set -e  # Exit on error

INSTALL_DIR="/home/jack/Simple-Uptime-Monitor"
SERVICE_NAME="Simple-Uptime-Monitor.service"
VENV_DIR="$INSTALL_DIR/venv"

# Change to installation directory
cd "$INSTALL_DIR"

echo "========================================="
echo "Simple Uptime Monitor Installation"
echo "========================================="
echo ""

# Detect environment
if grep -qi microsoft /proc/version; then
    echo "Detected: WSL (Windows Subsystem for Linux)"
elif [ -f /.dockerenv ]; then
    echo "Detected: Docker container"
else
    echo "Detected: Linux system"
fi
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "Error: Python 3.8+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "Python version OK: $PYTHON_VERSION"

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate venv and install dependencies
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

# Install the package in editable mode
echo "Installing uptime_monitor package..."
pip install -e "$INSTALL_DIR"

# Create data directory FIRST (before database init)
echo "Creating data directory..."
mkdir -p "$INSTALL_DIR/data"

# Initialize database (now that data directory exists)
echo "Initializing database..."
python3 -m uptime_monitor.database --init "$INSTALL_DIR/data/uptime.db"

# Copy default config if needed
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    echo "Creating default config.yaml..."
    cp "$INSTALL_DIR/config.default.yaml" "$INSTALL_DIR/config.yaml"
    echo "✓ Default configuration created (add monitors via web UI)"
fi

# Create .env file for secrets
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "Creating .env file for secrets..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo ".env file created - EDIT THIS FILE to add your secrets!"
fi

# Install systemd service (if systemd is available)
echo "Installing systemd service..."
if command -v systemctl &> /dev/null && systemctl is-system-running &> /dev/null 2>&1; then
    sudo cp "$INSTALL_DIR/install/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
    sudo systemctl daemon-reload
    echo "Systemd service installed successfully!"
    SYSTEMD_AVAILABLE=true
else
    echo "⚠ Systemd not available (common on WSL)"
    echo "  You can enable systemd in WSL2 or run manually"
    SYSTEMD_AVAILABLE=false
fi

echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo ""

if [ "$SYSTEMD_AVAILABLE" = true ]; then
    echo "Starting service with systemd..."
    sudo systemctl start Simple-Uptime-Monitor
    sudo systemctl enable Simple-Uptime-Monitor

    echo ""
    echo "✓ Service started and enabled for auto-start on boot"
    echo ""
    echo "Useful commands:"
    echo "  Check status:  sudo systemctl status Simple-Uptime-Monitor"
    echo "  View logs:     sudo journalctl -u Simple-Uptime-Monitor -f"
    echo "  Restart:       sudo systemctl restart Simple-Uptime-Monitor"
    echo "  Stop:          sudo systemctl stop Simple-Uptime-Monitor"
else
    echo "Starting service..."
    bash "$INSTALL_DIR/install/start.sh"

    echo ""
    echo "✓ Service started"
    echo ""
    echo "Useful commands:"
    echo "  Start service:   bash $INSTALL_DIR/install/start.sh"
    echo "  Stop service:    bash $INSTALL_DIR/install/stop.sh"
    echo "  View logs:       tail -f $INSTALL_DIR/data/uptime-monitor.log"
    echo ""

    if [ -f /.dockerenv ]; then
        echo "=== DOCKER AUTO-START ==="
        echo "To auto-start in Docker, use this Dockerfile CMD:"
        echo "  CMD [\"bash\", \"/home/jack/Simple-Uptime-Monitor/install/start.sh\"]"
        echo ""
    elif grep -qi microsoft /proc/version; then
        echo "=== WSL AUTO-START OPTIONS ==="
        echo ""
        echo "Option 1: Enable systemd in WSL (recommended)"
        echo "  1. Edit /etc/wsl.conf:"
        echo "       sudo nano /etc/wsl.conf"
        echo "  2. Add these lines:"
        echo "       [boot]"
        echo "       systemd=true"
        echo "  3. Restart WSL from PowerShell:"
        echo "       wsl.exe --shutdown"
        echo "  4. Re-run installer to set up systemd service"
        echo ""
        echo "Option 2: WSL boot command (requires WSL 0.67.6+)"
        echo "  1. Edit /etc/wsl.conf:"
        echo "       sudo nano /etc/wsl.conf"
        echo "  2. Add these lines:"
        echo "       [boot]"
        echo "       command=\"bash $INSTALL_DIR/install/start.sh\""
        echo "  3. Restart WSL from PowerShell:"
        echo "       wsl.exe --shutdown"
        echo ""
        echo "Option 3: Windows Task Scheduler"
        echo "  Create a task that runs on login:"
        echo "    wsl.exe -d <distro> -u <user> bash $INSTALL_DIR/install/start.sh"
        echo ""
    fi
fi

echo ""
echo "Web dashboard is now available at: http://localhost:5000"
echo "Add monitors via the UI at: http://localhost:5000/monitors/manage"
echo ""
