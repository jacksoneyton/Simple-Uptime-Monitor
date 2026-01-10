#!/bin/bash
# Uninstallation script for Simple Uptime Monitor
# Compatible with: WSL, Ubuntu, Docker containers

set -e  # Exit on error

INSTALL_DIR="/home/jack/Simple-Uptime-Monitor"
SERVICE_NAME="Simple-Uptime-Monitor.service"

echo "========================================="
echo "Simple Uptime Monitor Uninstaller"
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

# Warning
echo "⚠️  WARNING: This will remove Simple Uptime Monitor"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi
echo ""

# Stop and disable systemd service (if running)
if command -v systemctl &> /dev/null && systemctl --version &> /dev/null; then
    echo "Checking systemd service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "  Stopping service..."
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "  Disabling service..."
        sudo systemctl disable "$SERVICE_NAME"
    fi
    
    if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
        echo "  Removing service file..."
        sudo rm "/etc/systemd/system/$SERVICE_NAME"
        sudo systemctl daemon-reload
        echo "  ✓ Systemd service removed"
    else
        echo "  ℹ Service file not found (already removed or never installed)"
    fi
else
    echo "ℹ Systemd not available, skipping service removal"
fi
echo ""

# Ask about data removal
echo "What would you like to remove?"
echo ""
echo "1) Everything (service, venv, database, config, logs)"
echo "2) Service only (keep data and config)"
echo "3) Service + venv (keep database and config)"
echo "4) Cancel"
echo ""
read -p "Choose option [1-4]: " -n 1 -r
echo
echo ""

case $REPLY in
    1)
        echo "Removing everything..."
        
        # Remove virtual environment
        if [ -d "$INSTALL_DIR/venv" ]; then
            echo "  Removing virtual environment..."
            rm -rf "$INSTALL_DIR/venv"
        fi
        
        # Remove database and data
        if [ -d "$INSTALL_DIR/data" ]; then
            echo "  Removing database and data..."
            rm -rf "$INSTALL_DIR/data"
        fi
        
        # Remove config files
        if [ -f "$INSTALL_DIR/config.yaml" ]; then
            echo "  Removing config.yaml..."
            rm "$INSTALL_DIR/config.yaml"
        fi
        
        if [ -f "$INSTALL_DIR/.env" ]; then
            echo "  Removing .env..."
            rm "$INSTALL_DIR/.env"
        fi
        
        # Remove log files
        if [ -f "$INSTALL_DIR/data/uptime-monitor.log" ]; then
            echo "  Removing log files..."
            rm -f "$INSTALL_DIR/data/uptime-monitor.log"*
        fi
        
        echo ""
        echo "✓ Complete uninstallation finished"
        echo ""
        echo "Note: The source code directory remains at:"
        echo "  $INSTALL_DIR"
        echo ""
        echo "To completely remove the project:"
        echo "  cd .."
        echo "  rm -rf Simple-Uptime-Monitor"
        ;;
        
    2)
        echo "Removing service only..."
        echo ""
        echo "✓ Service removed (data and config preserved)"
        echo ""
        echo "To reinstall:"
        echo "  bash $INSTALL_DIR/install/install.sh"
        ;;
        
    3)
        echo "Removing service and virtual environment..."
        
        # Remove virtual environment
        if [ -d "$INSTALL_DIR/venv" ]; then
            echo "  Removing virtual environment..."
            rm -rf "$INSTALL_DIR/venv"
        fi
        
        echo ""
        echo "✓ Service and venv removed (data and config preserved)"
        echo ""
        echo "To reinstall:"
        echo "  bash $INSTALL_DIR/install/install.sh"
        ;;
        
    4)
        echo "Uninstallation cancelled."
        exit 0
        ;;
        
    *)
        echo "Invalid option. Uninstallation cancelled."
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "Uninstallation Complete"
echo "========================================="
echo ""
