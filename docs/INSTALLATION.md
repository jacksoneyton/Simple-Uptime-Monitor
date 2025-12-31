# Installation Guide

Complete installation instructions for Simple Uptime Monitor on WSL Ubuntu.

## Prerequisites

- **Operating System**: WSL Ubuntu (or any Linux distribution with systemd)
- **Python**: Version 3.8 or higher
- **Permissions**: Ability to run `sudo` commands
- **Network**: Internet access for downloading dependencies

## Quick Installation

### 1. Download/Clone the Project

```bash
cd /home/jack
# If using git:
# git clone <repository-url> Simple-Uptime-Monitor

cd Simple-Uptime-Monitor
```

### 2. Run the Installer

```bash
bash install/install.sh
```

The installation script will:
1. Verify Python 3.8+ is installed
2. Create a Python virtual environment in `venv/`
3. Install all required Python packages
4. Create the `data/` directory for the database
5. Copy `config.example.yaml` to `config.yaml`
6. Create `.env` from `.env.example`
7. Initialize the SQLite database
8. Install the systemd service

### 3. Configure Monitors

Edit `config.yaml` to define your monitors:

```bash
nano config.yaml
```

See [YAML_REFERENCE.md](YAML_REFERENCE.md) for complete configuration documentation.

### 4. Add Secrets

Edit `.env` to add your credentials and API keys:

```bash
nano .env
```

Example:
```bash
SMTP_PASSWORD=your_gmail_app_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Important**: Never commit `.env` to version control!

### 5. Start the Service

```bash
# Start the service
sudo systemctl start uptime-monitor

# Enable auto-start on boot
sudo systemctl enable uptime-monitor

# Check status
sudo systemctl status uptime-monitor
```

### 6. Access the Dashboard

Open your browser to: **http://localhost:5000**

If you configured a different host/port in `config.yaml`, use that instead.

---

## Manual Installation

If you prefer to install manually without the script:

### 1. Create Virtual Environment

```bash
cd /home/jack/Simple-Uptime-Monitor
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create Configuration

```bash
cp config.example.yaml config.yaml
cp .env.example .env

# Edit both files
nano config.yaml
nano .env
```

### 4. Initialize Database

```bash
mkdir -p data
python -m uptime_monitor.database --init data/uptime.db
```

### 5. Test Run (Optional)

Before installing as a service, test the application:

```bash
python -m uptime_monitor.main
```

Press `Ctrl+C` to stop.

### 6. Install Systemd Service

```bash
sudo cp install/uptime-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start uptime-monitor
sudo systemctl enable uptime-monitor
```

---

## Verification

### Check Service Status

```bash
sudo systemctl status uptime-monitor
```

You should see:
```
● uptime-monitor.service - Simple Uptime Monitor
   Loaded: loaded (/etc/systemd/system/uptime-monitor.service; enabled)
   Active: active (running) since ...
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u uptime-monitor -f

# View last 50 lines
sudo journalctl -u uptime-monitor -n 50

# View logs since last boot
sudo journalctl -u uptime-monitor -b
```

### Check Web Dashboard

```bash
# Test with curl
curl http://localhost:5000

# Or open in browser
xdg-open http://localhost:5000
```

### Verify Database

```bash
ls -lh data/uptime.db

# Should see the database file
-rw-r--r-- 1 jack jack 20K Dec 31 12:00 data/uptime.db
```

---

## Configuration Tips

### Setting up Email Notifications

For Gmail:
1. Enable 2-factor authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the app password in `.env`:
   ```bash
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

For other providers, use their SMTP settings:
- **Outlook**: smtp.office365.com:587
- **Yahoo**: smtp.mail.yahoo.com:587
- **Custom**: Check your email provider's documentation

### Setting up Discord Notifications

1. Open Discord server settings
2. Go to Integrations → Webhooks
3. Create New Webhook
4. Copy the Webhook URL
5. Add to `.env`:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

### Setting up Slack Notifications

1. Go to https://api.slack.com/apps
2. Create New App
3. Add Incoming Webhooks feature
4. Activate and create webhook for your channel
5. Copy Webhook URL to `.env`:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

---

## Updating

### Update Configuration

```bash
# Edit configuration
nano config.yaml

# Restart service to apply changes
sudo systemctl restart uptime-monitor
```

### Update Application Code

```bash
cd /home/jack/Simple-Uptime-Monitor

# Pull latest changes (if using git)
git pull

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart uptime-monitor
```

---

## Uninstalling

### 1. Stop and Disable Service

```bash
sudo systemctl stop uptime-monitor
sudo systemctl disable uptime-monitor
sudo rm /etc/systemd/system/uptime-monitor.service
sudo systemctl daemon-reload
```

### 2. Remove Application Files

```bash
cd /home/jack
rm -rf Simple-Uptime-Monitor
```

### 3. Remove Database (Optional)

The database is already removed with the application directory. If you moved it elsewhere:

```bash
rm /path/to/uptime.db
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
sudo journalctl -u uptime-monitor -n 50 --no-pager
```

**Common issues:**

1. **Configuration error**
   ```bash
   # Validate config
   cd /home/jack/Simple-Uptime-Monitor
   source venv/bin/activate
   python3 -c "from uptime_monitor.config import load_config; load_config()"
   ```

2. **Missing .env file**
   ```bash
   # Create from example
   cp .env.example .env
   # Edit and add values
   nano .env
   ```

3. **Permission issues**
   ```bash
   # Fix ownership
   sudo chown -R jack:jack /home/jack/Simple-Uptime-Monitor
   ```

4. **Port already in use**
   ```bash
   # Check what's using port 5000
   sudo lsof -i :5000

   # Change port in config.yaml if needed
   ```

### Database Errors

**Database locked:**
- SQLite doesn't handle high concurrency well
- Reduce number of concurrent monitors
- Increase check intervals

**Reset database:**
```bash
cd /home/jack/Simple-Uptime-Monitor
source venv/bin/activate
python -m uptime_monitor.database --init data/uptime.db
```

### Ping Not Working

Ping uses unprivileged ICMP which should work without root. If issues persist:

```bash
# Install required packages
sudo apt-get install iputils-ping

# Test manually
ping -c 3 google.com
```

### Python Module Not Found

```bash
# Reinstall dependencies
cd /home/jack/Simple-Uptime-Monitor
source venv/bin/activate
pip install --force-reinstall -r requirements.txt
```

---

## Advanced Configuration

### Running on Different Port

Edit `config.yaml`:
```yaml
global:
  web:
    port: 8080
```

Restart service:
```bash
sudo systemctl restart uptime-monitor
```

### Running Behind Reverse Proxy

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name uptime.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Setting Custom Database Location

Edit `config.yaml`:
```yaml
global:
  database: "/var/lib/uptime-monitor/uptime.db"
```

Create directory and set permissions:
```bash
sudo mkdir -p /var/lib/uptime-monitor
sudo chown jack:jack /var/lib/uptime-monitor
```

Update systemd service to allow write access:
```bash
sudo nano /etc/systemd/system/uptime-monitor.service

# Add to ReadWritePaths:
ReadWritePaths=/var/lib/uptime-monitor
```

---

## Next Steps

- Read [YAML_REFERENCE.md](YAML_REFERENCE.md) for complete configuration options
- Check [API.md](API.md) for push monitor API documentation
- Configure your monitors in `config.yaml`
- Set up notification channels
- Monitor the logs during initial operation

---

For additional support, check the project README or create an issue.
