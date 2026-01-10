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

# Copy example config if needed
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    echo "Creating config.yaml from example..."
    cp "$INSTALL_DIR/config.example.yaml" "$INSTALL_DIR/config.yaml"
    echo "IMPORTANT: Edit config.yaml to add your monitors and notification settings!"
fi

# Create .env file for secrets
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "Creating .env file for secrets..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo ".env file created - EDIT THIS FILE to add your secrets!"
fi

# Install systemd service (if systemd is available)
echo "Installing systemd service..."
if command -v systemctl &> /dev/null && systemctl --version &> /dev/null; then
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
echo "Next steps:"
echo "  1. Edit config.yaml to configure your monitors"
echo "  2. Edit .env to add your secrets (SMTP password, webhook URLs, etc.)"
echo ""

if [ "$SYSTEMD_AVAILABLE" = true ]; then
    echo "  3. Start the service:"
    echo "     sudo systemctl start Simple-Uptime-Monitor"
    echo "  4. Enable auto-start on boot:"
    echo "     sudo systemctl enable Simple-Uptime-Monitor"
    echo "  5. Check status:"
    echo "     sudo systemctl status Simple-Uptime-Monitor"
    echo "  6. View logs:"
    echo "     sudo journalctl -u Simple-Uptime-Monitor -f"
else
    echo "  3. Running without systemd:"
    echo ""
    if grep -qi microsoft /proc/version; then
        echo "     WSL: Enable systemd (recommended):"
        echo "       Add to /etc/wsl.conf:"
        echo "       [boot]"
        echo "       systemd=true"
        echo "       Then restart WSL: wsl.exe --shutdown"
        echo ""
    fi
    echo "     OR run manually:"
    echo "       cd $INSTALL_DIR"
    echo "       source venv/bin/activate"
    echo "       python -m uptime_monitor.main"
    echo ""
    if [ -f /.dockerenv ]; then
        echo "     Docker: Use the manual command as your ENTRYPOINT/CMD"
    fi
fi

echo ""
echo "Web dashboard will be available at: http://localhost:5000"
echo ""
