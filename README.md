# Simple Uptime Monitor

A simple, YAML-configured uptime monitoring system with a web dashboard - inspired by Uptime Kuma but designed for simplicity and minimal dependencies.

## Features

- **Multiple Monitor Types**: HTTP/HTTPS, TCP, Ping (ICMP), DNS, WebSocket, Docker containers, and push-based monitoring
- **YAML Configuration**: Define all monitors in a simple YAML file
- **Web Dashboard**: Real-time status dashboard with grouping and history charts
- **Notifications**: Email (SMTP), Discord, and Slack webhook support
- **SQLite Database**: Lightweight persistence with history tracking
- **Systemd Service**: Runs as a background service on Linux
- **SSL Certificate Monitoring**: Automatic SSL expiration alerts
- **Incident Tracking**: Automatic downtime incident management
- **Multi-Platform**: WSL, Ubuntu/Debian, and Docker support
- **Web UI Management**: Add, edit, and delete monitors via web interface
- **Cyberpunk Theme**: Dark, neon-glowing aesthetic with real-time updates

## Quick Start

### 1. Installation

The installer supports **WSL**, **Ubuntu/Debian**, and **Docker**:

```bash
cd /home/jack/Simple-Uptime-Monitor
bash install/install.sh
```

The installer will:
- Auto-detect your environment (WSL/Docker/Linux)
- Create a Python virtual environment
- Install all dependencies
- Initialize the SQLite database
- Create a minimal working configuration
- Install and **start** the service automatically
- Set up auto-start on boot (systemd or alternatives)

### 2. Access the Dashboard

The service starts automatically after installation!

Open your browser to: **http://localhost:5000**

### 3. Add Monitors

**No configuration file editing required!** Add monitors via the web UI:

1. Navigate to **http://localhost:5000/monitors/manage**
2. Click "Add New Monitor"
3. Fill in the monitor details (name, type, URL, etc.)
4. Save - the monitor starts checking immediately

### 4. Optional: Configure Notifications

To receive alerts, edit `.env` with your notification credentials:

```bash
SMTP_PASSWORD=your_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Then add notification channels via the web UI or edit `config.yaml`

### 5. Service Management

**With systemd (Ubuntu/Debian):**
```bash
sudo systemctl status Simple-Uptime-Monitor  # Check status
sudo systemctl restart Simple-Uptime-Monitor # Restart
sudo systemctl stop Simple-Uptime-Monitor    # Stop
sudo journalctl -u Simple-Uptime-Monitor -f  # View logs
```

**Without systemd (WSL/Docker):**
```bash
bash install/start.sh                        # Start service
bash install/stop.sh                         # Stop service
tail -f data/uptime-monitor.log              # View logs
```

## Monitor Types

| Type | Description | Example Use Case |
|------|-------------|------------------|
| **HTTP/HTTPS** | Monitor web services with keyword/JSON validation | Websites, APIs, health endpoints |
| **TCP** | Check if a port is accepting connections | Databases, SSH, custom services |
| **Ping** | ICMP echo requests | Network devices, servers |
| **DNS** | Validate DNS resolution | Domain records, nameserver checks |
| **WebSocket** | Monitor WebSocket endpoints | Real-time services |
| **Docker** | Check container health status | Containerized apps |
| **Push** | Passive monitoring via API pushes | Cron jobs, backup scripts |

## Notification Channels

- **Email (SMTP)**: Standard email notifications
- **Discord**: Webhook-based Discord messages
- **Slack**: Webhook-based Slack messages

Each monitor can trigger different notification channels on state changes (up, down, SSL expiration).

## Project Structure

```
Simple-Uptime-Monitor/
├── uptime_monitor/          # Main Python package
│   ├── monitors/            # Monitor implementations
│   ├── notifications/       # Notification handlers
│   ├── templates/           # Jinja2 templates
│   ├── main.py             # Application entry point
│   ├── config.py           # YAML configuration loader
│   ├── database.py         # SQLAlchemy models
│   ├── scheduler.py        # Monitor orchestration
│   └── webapp.py           # Flask web application
├── static/                  # CSS and JavaScript
├── data/                    # SQLite database
├── install/                 # Installation scripts
├── docs/                    # Documentation
├── config.yaml             # Your configuration
├── .env                    # Secrets (gitignored)
└── requirements.txt        # Python dependencies
```

## Documentation

- **[Installation Guide](docs/INSTALLATION.md)**: Detailed installation instructions
- **[YAML Reference](docs/YAML_REFERENCE.md)**: Complete configuration documentation
- **[Push Monitor API](docs/API.md)**: API documentation for push monitors

## Configuration Example

See `config.example.yaml` for a comprehensive example with all monitor types and options.

## Development

### Running Locally (Without Systemd)

```bash
# Activate virtual environment
source venv/bin/activate

# Run directly
python -m uptime_monitor.main
```

### Database Management

```bash
# Initialize/reset database
python -m uptime_monitor.database --init data/uptime.db
```

## Requirements

- Python 3.8+
- Linux with systemd (tested on WSL Ubuntu)
- SQLite 3

## License

This project is provided as-is for personal and commercial use.

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u uptime-monitor -n 50

# Verify configuration
python3 -c "from uptime_monitor.config import load_config; load_config()"
```

### Ping monitors not working

Ping monitors use unprivileged ICMP which should work without root on most systems. If you encounter issues, check that `icmplib` is properly installed.

### Database locked errors

SQLite doesn't handle high write concurrency well. If you're monitoring hundreds of services, consider:
- Increasing check intervals
- Reducing retry counts
- Limiting concurrent checks

## Support

For issues and feature requests, please create an issue in the project repository.

---

**Simple Uptime Monitor** - Monitor your services with simplicity.

## Deployment Options

### Ubuntu/Debian (with systemd)

The installer automatically starts the service and enables auto-start on boot:

```bash
bash install/install.sh
# Service is now running! Access: http://localhost:5000
```

Manage the service:
```bash
sudo systemctl status Simple-Uptime-Monitor   # Check status
sudo systemctl restart Simple-Uptime-Monitor  # Restart
sudo journalctl -u Simple-Uptime-Monitor -f   # View logs
```

### WSL (Windows Subsystem for Linux)

The installer automatically starts the service. For auto-start on boot, choose one of these options:

**Option 1: Enable systemd in WSL (recommended)**
```bash
# Edit /etc/wsl.conf
sudo nano /etc/wsl.conf

# Add these lines:
[boot]
systemd=true

# Restart WSL from PowerShell
wsl.exe --shutdown

# Re-run installer to set up systemd service
bash install/install.sh
```

**Option 2: WSL boot command (WSL 0.67.6+)**
```bash
# Edit /etc/wsl.conf
sudo nano /etc/wsl.conf

# Add this line:
[boot]
command="bash /home/jack/Simple-Uptime-Monitor/install/start.sh"

# Restart WSL from PowerShell
wsl.exe --shutdown
```

**Option 3: Manual control**
```bash
bash install/start.sh  # Start service
bash install/stop.sh   # Stop service
```

### Docker

```bash
# Build the image
docker build -t simple-uptime-monitor .

# Run with persistent data
docker run -d \
  --name uptime-monitor \
  -p 5000:5000 \
  -v $(pwd)/config.yaml:/opt/Simple-Uptime-Monitor/config.yaml \
  -v $(pwd)/data:/opt/Simple-Uptime-Monitor/data \
  simple-uptime-monitor

# View logs
docker logs -f uptime-monitor
```

## Uninstallation

```bash
bash install/uninstall.sh
```

The uninstaller provides options to:
1. **Remove everything** - Service, venv, database, config, logs
2. **Remove service only** - Keep data and config for reinstall
3. **Remove service + venv** - Keep database and config
4. **Cancel** - Exit without changes

## Web Interface

After installation, access the web dashboard at:
- **URL**: http://localhost:5000
- **Manage Monitors**: http://localhost:5000/monitors/manage

Features:
- Real-time status updates (5-second polling)
- Add/edit/delete monitors via web UI
- Response time graphs (Chart.js)
- Incident tracking with history
- Grouped monitor display
- Hot-reload configuration (no restart needed)

