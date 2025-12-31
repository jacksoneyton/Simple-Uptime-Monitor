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
- **Simple Installation**: Single installation script for WSL Ubuntu

## Quick Start

### 1. Installation

```bash
cd /home/jack/Simple-Uptime-Monitor
bash install/install.sh
```

The installer will:
- Create a Python virtual environment
- Install all dependencies
- Initialize the SQLite database
- Create configuration templates
- Install the systemd service

### 2. Configuration

Edit `config.yaml` to add your monitors:

```yaml
monitors:
  - name: "My Website"
    type: "http"
    enabled: true
    group: "Production Services"
    interval: 30
    config:
      url: "https://example.com"
      expected_status_codes: [200]
    notifications:
      - "admin_email"
    alert_on:
      - down
      - up
```

Add secrets to `.env`:

```bash
SMTP_PASSWORD=your_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 3. Start the Service

```bash
# Start now
sudo systemctl start uptime-monitor

# Enable auto-start on boot
sudo systemctl enable uptime-monitor

# Check status
sudo systemctl status uptime-monitor

# View logs
sudo journalctl -u uptime-monitor -f
```

### 4. Access the Dashboard

Open your browser to: **http://localhost:5000**

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
