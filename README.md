# Simple Uptime Monitor

A simple, Docker-based uptime monitoring system with a web dashboard - inspired by Uptime Kuma but designed for simplicity and minimal dependencies.

## Features

- **Multiple Monitor Types**: HTTP/HTTPS, TCP, Ping (ICMP), DNS, WebSocket, Docker containers, and push-based monitoring
- **YAML Configuration**: Define all monitors in a simple YAML file
- **Web Dashboard**: Real-time status dashboard with grouping and history charts
- **Notifications**: Email (SMTP), Discord, and Slack webhook support
- **SQLite Database**: Lightweight persistence with history tracking
- **SSL Certificate Monitoring**: Automatic SSL expiration alerts
- **Incident Tracking**: Automatic downtime incident management
- **Web UI Management**: Add, edit, and delete monitors via web interface
- **Cyberpunk Theme**: Dark, neon-glowing aesthetic with real-time updates
- **Docker Native**: Single command deployment

## Quick Start (Docker)

### Option 1: Docker Compose (Recommended)

```bash
mkdir simple-uptime-monitor
cd simple-uptime-monitor
curl -o compose.yaml https://raw.githubusercontent.com/jacksoneyton/Simple-Uptime-Monitor/main/compose.yaml
docker compose up -d
```

### Option 2: Docker Run

```bash
docker run -d \
  --restart=unless-stopped \
  -p 5000:5000 \
  -v uptime-monitor:/app/data \
  --name simple-uptime-monitor \
  ghcr.io/jacksoneyton/simple-uptime-monitor:latest
```

That's it! The service is now running at **http://localhost:5000**

### Add Monitors

Navigate to **http://localhost:5000/monitors/manage** and click "Add New Monitor"

No configuration file editing required - add everything via the web UI!

## Configuration

### Basic Setup

The default configuration works out of the box. To customize:

1. **Edit config.yaml** (optional) - set timezone, intervals, etc.
2. **Edit .env** (for notifications) - add SMTP passwords, webhook URLs

```bash
# .env example
SMTP_PASSWORD=your_smtp_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Persistent Data

Data is persisted in the `./data` directory:
- `data/uptime.db` - SQLite database with all history
- `data/uptime-monitor.log` - Application logs

### Docker Compose Options

```yaml
services:
  uptime-monitor:
    ports:
      - "5000:5000"      # Change port if needed
    environment:
      - TZ=America/New_York  # Set your timezone
    restart: unless-stopped  # Auto-restart on failure
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

Configure notification channels in `config.yaml` or via the web UI.

## Docker Commands

```bash
# Start the service
docker compose up -d

# View logs
docker compose logs -f

# Stop the service
docker compose down

# Restart the service
docker compose restart

# Rebuild after code changes
docker compose up -d --build

# Remove everything (including data)
docker compose down -v
```

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
├── data/                    # SQLite database (persistent)
├── config.yaml             # Your configuration
├── .env                    # Secrets (gitignored)
├── Dockerfile              # Docker image definition
├── compose.yaml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

## Documentation

- **[YAML Reference](docs/YAML_REFERENCE.md)**: Complete configuration documentation
- **[Push Monitor API](docs/API.md)**: API documentation for push monitors
- **[Installation Guide](docs/INSTALLATION.md)**: Bare-metal installation (alternative to Docker)

## Advanced Usage

### Custom Network

```yaml
# compose.yaml
services:
  uptime-monitor:
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### Environment Variables

All configuration values support environment variable substitution:

```yaml
# config.yaml
notifications:
  - name: "email"
    type: "email"
    config:
      smtp_password: "${SMTP_PASSWORD}"
      smtp_host: "${SMTP_HOST:-smtp.gmail.com}"
```

### Monitoring Other Docker Containers

```yaml
# compose.yaml
services:
  uptime-monitor:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Then add Docker monitors via the web UI.

## Web Interface

Access the dashboard at **http://localhost:5000**

Features:
- Real-time status updates (5-second polling)
- Add/edit/delete monitors via web UI
- Response time graphs (Chart.js)
- Incident tracking with history
- Grouped monitor display
- Hot-reload configuration (no restart needed)
- Cyberpunk theme with neon glow effects

## Troubleshooting

### Service won't start

```bash
# Check logs
docker compose logs uptime-monitor

# Check if port 5000 is already in use
sudo netstat -tulpn | grep 5000

# Change port in compose.yaml if needed
ports:
  - "5001:5000"
```

### Database locked errors

SQLite doesn't handle high write concurrency well. If monitoring hundreds of services:
- Increase check intervals
- Reduce retry counts
- Consider PostgreSQL for very large deployments

### Ping monitors not working in Docker

Ping requires elevated privileges. Add to compose.yaml:

```yaml
services:
  uptime-monitor:
    cap_add:
      - NET_RAW
```

## Development

### Running Locally Without Docker

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Initialize database
python -m uptime_monitor.database --init data/uptime.db

# Run the application
python -m uptime_monitor.main
```

### Making Changes

```bash
# Edit code
vim uptime_monitor/...

# Rebuild and restart
docker compose up -d --build
```

## Requirements

- Docker 20.10+
- Docker Compose 1.29+

OR for bare-metal installation:
- Python 3.8+
- SQLite 3

## License

This project is provided as-is for personal and commercial use.

## Support

For issues and feature requests, please create an issue in the project repository.

---

**Simple Uptime Monitor** - Monitor your services with simplicity.

## Alternative Installation (Bare Metal)

If you prefer not to use Docker, you can install directly on:
- Ubuntu/Debian with systemd
- WSL (Windows Subsystem for Linux)

See **[Installation Guide](docs/INSTALLATION.md)** for detailed instructions.

Quick install:
```bash
cd Simple-Uptime-Monitor
bash install/install.sh
```

Note: Docker deployment is recommended for simplicity and portability.
