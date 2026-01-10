#!/bin/bash
# Installation script for Simple Uptime Monitor on WSL Ubuntu

set -e  # Exit on error

INSTALL_DIR="/home/jack/Simple-Uptime-Monitor"
SERVICE_NAME="Simple-Uptime-Monitor.service"
VENV_DIR="$INSTALL_DIR/venv"

echo "========================================="
echo "Simple Uptime Monitor Installation"
echo "========================================="

# Check if running on WSL
if ! grep -qi microsoft /proc/version; then
    echo "Warning: This script is designed for WSL Ubuntu"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

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

# Create data directory
echo "Creating data directory..."
mkdir -p "$INSTALL_DIR/data"

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

# Initialize database
echo "Initializing database..."
python3 -m uptime_monitor.database --init data/uptime.db

# Install systemd service
echo "Installing systemd service..."
sudo cp "$INSTALL_DIR/install/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
sudo systemctl daemon-reload

echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit config.yaml to configure your monitors"
echo "  2. Edit .env to add your secrets (SMTP password, webhook URLs, etc.)"
echo "  3. Start the service:"
echo "     sudo systemctl start Simple-Uptime-Monitor"
echo "  4. Enable auto-start on boot:"
echo "     sudo systemctl enable Simple-Uptime-Monitor"
echo "  5. Check status:"
echo "     sudo systemctl status Simple-Uptime-Monitor"
echo "  6. View logs:"
echo "     sudo journalctl -u Simple-Uptime-Monitor -f"
echo ""
echo "Web dashboard will be available at: http://localhost:5000"
echo ""
