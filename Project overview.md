# Simple Uptime Monitor - Project Overview & Implementation Guide

## Project Summary

A lightweight uptime monitoring system built with Python and Flask. Provides YAML-based configuration, multiple monitor types, real-time web dashboard, and systemd service integration for Linux systems.

## Implemented Features

### Monitoring Capabilities
- **HTTP/HTTPS**: Keyword search, JSON path validation, custom headers, authentication support
- **TCP Port**: Port connectivity checks
- **Ping (ICMP)**: Host reachability monitoring
- **DNS**: Record resolution with type support and expected value validation
- **Docker**: Container status monitoring
- **Push/Heartbeat**: Monitoring for cron jobs and scheduled tasks

### Core Features
- YAML configuration files
- Web dashboard with real-time updates
- Monitor grouping
- SQLite database for persistence
- Uptime statistics and response time tracking
- Downtime event tracking
- Configurable check intervals per monitor
- Retry logic for unreliable connections
- systemd service integration

### Developer Features
- Clean code structure
- Comprehensive documentation
- Example configurations
- Installation automation
- Management scripts
- Error handling and logging

## Architecture

### Component Overview

```
┌─────────────────┐
│  Web Dashboard  │ (Flask + HTML/CSS/JS)
│  Port 3001      │
└────────┬────────┘
         │
┌────────▼────────┐
│   Flask App     │ (API endpoints)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────┐
│Sched │  │  DB   │
│uler  │  │SQLite │
└───┬──┘  └───────┘
    │
┌───▼────────┐
│  Monitors  │ (Check implementations)
└────────────┘
```

### File Structure

```
simple-uptime-monitor/
├── src/                      # Core application code
│   ├── __init__.py          # Package initializer
│   ├── app.py               # Flask web application and API
│   ├── monitors.py          # Monitor check implementations
│   ├── scheduler.py         # Monitoring scheduler
│   ├── database.py          # SQLite database layer
│   └── config_loader.py     # YAML configuration loader
│
├── templates/               # Web templates
│   └── index.html          # Dashboard UI
│
├── config/                  # Configuration files
│   ├── example.yaml        # Example configuration
│   └── monitors.yaml       # Actual configuration (created on install)
│
├── docs/                    # Documentation
│   ├── YAML_REFERENCE.md   # Complete YAML reference
│   └── QUICKSTART.md       # Quick start guide
│
├── scripts/                 # Utility scripts
│   └── manage.sh           # Management script
│
├── main.py                  # Application entry point
├── install.sh              # Installation script
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── .gitignore             # Git ignore rules
```

## Code Quality & Best Practices

### 1. Clean Architecture
- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Dependency Injection**: Flask app receives configured dependencies
- **Factory Pattern**: Monitor creation uses factory pattern for extensibility

### 2. Error Handling
- Try-catch blocks around all I/O operations
- Graceful degradation on failures
- Comprehensive logging at all levels
- User-friendly error messages

### 3. Configuration
- Type validation for all configuration fields
- Required field checking
- Descriptive error messages for configuration issues
- Support for multiple configuration files

### 4. Database Design
- Normalized schema
- Indexed queries for performance
- Automatic cleanup of old data
- Transaction handling for data integrity

### 5. Monitoring Design
- Retries for transient failures
- Configurable timeouts
- Response time tracking
- Uptime percentage calculation
- Downtime event tracking

## Installation & Deployment

### Quick Installation

```bash
cd simple-uptime-monitor
chmod +x install.sh
./install.sh
```

The installer performs the following:
1. Checks Python version
2. Creates virtual environment
3. Installs dependencies
4. Sets up directories
5. Creates systemd service
6. Sets proper permissions

### Manual Installation

For manual installation:

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create directories:**
```bash
mkdir -p logs data config
```

4. **Create configuration:**
```bash
cp config/example.yaml config/monitors.yaml
# Edit config/monitors.yaml
```

5. **Run application:**
```bash
python3 main.py
```

### Service Management

Management script usage:

```bash
# Make executable
chmod +x scripts/manage.sh

# Show help
./scripts/manage.sh help

# Common operations
./scripts/manage.sh start       # Start service
./scripts/manage.sh stop        # Stop service
./scripts/manage.sh restart     # Restart service
./scripts/manage.sh logs        # View logs
./scripts/manage.sh validate    # Validate config
./scripts/manage.sh edit        # Edit config
```

## Configuration Guide

### Minimal Configuration

```yaml
groups:
  - name: Services
    monitors:
      - name: Website
        type: http
        url: https://example.com
```

### Production Configuration

```yaml
settings:
  retention_days: 30

groups:
  - name: Web Services
    description: Public-facing services
    monitors:
      - name: Main Website
        type: https
        url: https://example.com
        interval: 60
        expected_status: [200, 301]
        keyword: "Welcome"
        verify_ssl: true
        
      - name: API Health
        type: https
        url: https://api.example.com/health
        method: GET
        expected_status: 200
        json_path: "status"
        headers:
          Authorization: Bearer YOUR_TOKEN
        interval: 30
        retries: 2

  - name: Infrastructure
    description: Core infrastructure
    monitors:
      - name: Database
        type: tcp
        host: db.example.com
        port: 5432
        interval: 120
        timeout: 5
        
      - name: DNS
        type: dns
        hostname: example.com
        record_type: A
        interval: 300
        
      - name: Gateway
        type: ping
        host: 192.168.1.1
        interval: 60

monitors:
  - name: App Container
    type: docker
    container_name: my-app
    interval: 60
    
  - name: Backup Job
    type: push
    grace_period: 3600
```

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get all monitor statuses |
| `/api/groups` | GET | Get monitor groups |
| `/api/monitor/<name>` | GET | Get monitor details |
| `/api/monitor/<name>/check` | POST | Trigger manual check |
| `/api/push/<name>` | POST/GET | Push endpoint |
| `/api/scheduler/info` | GET | Scheduler information |
| `/api/stats/summary` | GET | Overall statistics |
| `/api/health` | GET | Health check |

### Example API Usage

```bash
# Get all statuses
curl http://localhost:3001/api/status

# Trigger manual check
curl -X POST http://localhost:3001/api/monitor/Website/check

# Push heartbeat
curl http://localhost:3001/api/push/Backup%20Job

# Get monitor details
curl http://localhost:3001/api/monitor/Website
```

## Extending the System

### Adding a New Monitor Type

1. Create monitor class in `src/monitors.py`:

```python
class NewMonitorCheck(MonitorCheck):
    def check(self) -> Dict[str, Any]:
        # Implementation
        return self._create_result(is_up, response_time, message)
```

2. Register in `MONITOR_TYPES` dict:

```python
MONITOR_TYPES = {
    # ...
    'newtype': NewMonitorCheck,
}
```

3. Update documentation

### Adding Notifications

To add notification support:

1. Create `src/notifications.py`:
```python
class NotificationManager:
    def send_alert(self, monitor, result):
        # Send to configured channels
        pass
```

2. Integrate in scheduler:
```python
def _run_monitor(self, monitor_name):
    result = monitor.check()
    if not result['is_up']:
        self.notification_manager.send_alert(monitor, result)
```

3. Update configuration schema

## Performance Considerations

### Resource Usage
- **Memory**: 50-100MB for typical deployment
- **CPU**: Minimal (less than 1% on average)
- **Disk**: Grows with retention period
  - Approximately 1MB per 10,000 checks
  - Use `retention_days` setting to control

### Optimization

1. **Interval Selection**:
   - Critical services: 30-60 seconds
   - Normal priority: 120-300 seconds
   - Low priority: 600 seconds or more

2. **Database Maintenance**:
   - Automatic cleanup runs based on `retention_days`
   - Manual cleanup: `./scripts/manage.sh clean`

3. **Concurrent Checks**:
   - Each monitor runs in separate thread
   - No blocking between monitors

## Security Considerations

### Current Security

1. No authentication - Dashboard is open
2. No encryption - HTTP only
3. Local binding - Binds to 0.0.0.0

### Production Hardening

For production deployment:

1. **Add reverse proxy** (nginx):
```nginx
server {
    listen 443 ssl;
    server_name monitor.example.com;
    
    ssl_certificate /path/to/cert;
    ssl_certificate_key /path/to/key;
    
    location / {
        proxy_pass http://localhost:3001;
    }
}
```

2. **Add authentication**:
   - Basic auth at nginx level
   - Or implement in Flask app

3. **Firewall rules**:
```bash
sudo ufw allow from YOUR_IP to any port 3001
```

4. **Secure push endpoints**:
   - Add token validation
   - IP whitelisting

## Troubleshooting Guide

### Service Issues

**Service won't start:**
```bash
# Check systemd status
sudo systemctl status simple-uptime-monitor

# View detailed logs
sudo journalctl -u simple-uptime-monitor -n 100

# Check Python errors
/opt/simple-uptime-monitor/venv/bin/python3 /opt/simple-uptime-monitor/main.py
```

**Monitors not running:**
```bash
# Check scheduler
curl http://localhost:3001/api/scheduler/info

# View monitor logs
tail -f /opt/simple-uptime-monitor/logs/monitor.log
```

### Configuration Issues

**YAML syntax errors:**
```bash
# Validate YAML
./scripts/manage.sh validate

# Or manually
python3 -c "import yaml; yaml.safe_load(open('config/monitors.yaml'))"
```

**Monitor configuration errors:**
- Check required fields for monitor type
- Verify URL/host/port are correct
- Review logs for validation messages

### Network Issues

**Can't reach monitors:**
```bash
# Test from command line
curl -v https://your-site.com
ping your-host.com
nc -zv host port

# Check from WSL
ip route show
```

**Dashboard not accessible:**
```bash
# Verify service is listening
netstat -tlnp | grep 3001

# Test locally
curl http://localhost:3001/api/health

# Get WSL IP
ip addr show eth0 | grep inet
```

## Testing

### Manual Testing

```bash
# Start in development mode
python3 main.py

# Test monitors individually
curl http://localhost:3001/api/monitor/Website/check

# View real-time logs
tail -f logs/monitor.log
```

### Test Configuration

Create `config/test.yaml`:
```yaml
groups:
  - name: Test
    monitors:
      - name: Google
        type: http
        url: https://google.com
        interval: 30
```

## Maintenance

### Regular Tasks

1. **Review logs** (weekly):
```bash
./scripts/manage.sh logs
```

2. **Check disk space** (monthly):
```bash
du -sh /opt/simple-uptime-monitor/data
```

3. **Backup configuration** (before changes):
```bash
./scripts/manage.sh backup
```

4. **Update dependencies** (quarterly):
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Database Maintenance

```bash
# Check database size
du -h /opt/simple-uptime-monitor/data/monitor.db

# Clean old data (keeps retention_days)
# Automatic, or manual:
./scripts/manage.sh clean
```

## Future Enhancements

Potential improvements not currently implemented:

1. **Notifications**:
   - Email alerts
   - Slack integration
   - Discord webhooks
   - Custom webhooks

2. **Advanced Features**:
   - Public status pages
   - Multi-user support
   - API authentication
   - Grafana integration
   - Custom alert rules
   - SLA tracking

3. **Monitor Types**:
   - MySQL direct connection
   - PostgreSQL direct connection
   - MongoDB health checks
   - SSL certificate expiry
   - Kubernetes pods

4. **UI Enhancements**:
   - Dark mode
   - Mobile app
   - Charts and graphs
   - Historical comparison

## Additional Resources

- **README.md**: Project overview and setup
- **YAML_REFERENCE.md**: Complete configuration reference
- **QUICKSTART.md**: Quick setup guide
- **Example Config**: `config/example.yaml`

## Support

For issues or questions:
1. Check documentation
2. Review logs
3. Validate configuration
4. Create GitHub issue with details
