# Push Monitor API Documentation

API documentation for push-based passive monitoring.

## Overview

Push monitors are passive - instead of Simple Uptime Monitor checking your service, your service "pushes" status updates to the monitor. This is useful for:

- **Cron jobs**: Report completion after each run
- **Backup scripts**: Confirm backups completed successfully
- **Batch processes**: Monitor long-running tasks
- **Scheduled tasks**: Any periodic operation

If a push isn't received within the expected interval + grace period, the monitor is marked as DOWN and alerts are triggered.

---

## Creating a Push Monitor

### 1. Define in config.yaml

```yaml
monitors:
  - name: "Daily Backup Job"
    type: "push"
    enabled: true
    group: "Maintenance Tasks"

    config:
      expected_interval: 86400  # 24 hours in seconds
      grace_period: 3600        # 1 hour grace period (25 hours total)
      require_payload: false    # Optional status data

    notifications:
      - "admin_email"
    alert_on:
      - down  # Alert if push doesn't arrive
      - up    # Alert when push resumes
```

### 2. Get the Push URL

After the monitor runs its first check, it will generate a secret key. You can find this in the monitor metadata or logs.

The push URL format is:
```
http://your-server:5000/api/push/<monitor_id>/<secret_key>
```

**Example:**
```
http://localhost:5000/api/push/5/a7f3k9m2p8q1w4e6r9t2y5u8i0o3p6
```

### 3. View the Secret Key

Check the application logs or database:

```bash
# From logs
sudo journalctl -u uptime-monitor | grep "Push monitor initialized"

# Or query database
sqlite3 data/uptime.db "SELECT monitor_id, secret_key FROM push_monitors;"
```

---

## API Endpoints

### POST/GET /api/push/<monitor_id>/<secret_key>

Send a push update to mark the monitor as active.

#### Request

**Method:** `POST` or `GET`
**URL:** `/api/push/<monitor_id>/<secret_key>`

**Parameters:**
- `monitor_id` (path): Monitor ID from database
- `secret_key` (path): Auto-generated secret key

**Body:** Optional JSON payload (if `require_payload: true`)

```json
{
  "status": "success",
  "message": "Backup completed",
  "details": {
    "files_backed_up": 1234,
    "duration_seconds": 45
  }
}
```

#### Response

**Success (200 OK):**
```json
{
  "success": true,
  "monitor_id": 5,
  "received_at": "2025-01-15T10:30:00Z",
  "next_expected_by": "2025-01-16T11:30:00Z"
}
```

**Errors:**

- **404 Not Found**: Push monitor doesn't exist
  ```json
  {
    "error": "Push monitor not found"
  }
  ```

- **403 Forbidden**: Invalid secret key
  ```json
  {
    "error": "Invalid secret key"
  }
  ```

- **500 Internal Server Error**: Server error
  ```json
  {
    "error": "Internal server error"
  }
  ```

---

## Integration Examples

### Bash Script

```bash
#!/bin/bash
# Daily backup script with push monitoring

PUSH_URL="http://localhost:5000/api/push/5/a7f3k9m2p8q1w4e6r9t2y5u8i0o3p6"

# Run your backup
/usr/local/bin/backup.sh

# If backup succeeded, send push
if [ $? -eq 0 ]; then
    curl -X POST "$PUSH_URL" \
        -H "Content-Type: application/json" \
        -d '{"status": "success", "message": "Backup completed"}'
fi
```

### Python Script

```python
import requests
import sys

PUSH_URL = "http://localhost:5000/api/push/5/a7f3k9m2p8q1w4e6r9t2y5u8i0o3p6"

def send_push(status="success", message="Task completed"):
    """Send push update to monitor"""
    try:
        response = requests.post(PUSH_URL, json={
            "status": status,
            "message": message
        }, timeout=10)

        response.raise_for_status()
        print(f"Push sent successfully: {response.json()}")
        return True
    except requests.RequestException as e:
        print(f"Failed to send push: {e}", file=sys.stderr)
        return False

# Your task logic here
try:
    # ... do work ...
    send_push("success", "Data processing completed")
except Exception as e:
    send_push("error", f"Task failed: {str(e)}")
    raise
```

### Cron Job

```cron
# Send push every day at 2 AM
0 2 * * * curl -X POST http://localhost:5000/api/push/5/SECRET_KEY_HERE

# Or with a script
0 2 * * * /home/jack/scripts/backup.sh && curl -X POST http://localhost:5000/api/push/5/SECRET_KEY_HERE
```

### PowerShell (Windows)

```powershell
# Push monitoring for Windows scheduled task
$pushUrl = "http://wsl-server:5000/api/push/5/SECRET_KEY_HERE"

$payload = @{
    status = "success"
    message = "Windows backup completed"
} | ConvertTo-Json

Invoke-RestMethod -Uri $pushUrl -Method Post -Body $payload -ContentType "application/json"
```

### Docker Container

Add to your container's entrypoint or healthcheck:

```dockerfile
# In your Dockerfile or docker-compose.yml
HEALTHCHECK --interval=1h --timeout=10s \
    CMD curl -f http://uptime-monitor:5000/api/push/5/SECRET_KEY || exit 1
```

---

## Monitoring Behavior

### Timeline Example

Let's say you configure:
```yaml
expected_interval: 86400  # 24 hours
grace_period: 3600        # 1 hour
```

**Timeline:**
1. **12:00 PM**: First push received → Monitor is UP
2. **Next expected**: Tomorrow at 12:00 PM
3. **Grace period**: Until tomorrow at 1:00 PM
4. **1:01 PM** (next day): No push received → Monitor goes DOWN → Alerts sent
5. **2:00 PM**: Push received → Monitor recovers UP → Recovery alert sent

### State Transitions

```
NO PUSH YET → (first push) → UP
    ↓
    ↓ (deadline + grace expired)
    ↓
   DOWN → (push received) → UP
```

### Check Frequency

Push monitors are checked at the same frequency as other monitors (based on their `interval` setting, or the global `default_interval`). Each check verifies whether a push is overdue.

---

## Best Practices

### 1. Secure Your Secret Key

- **Never commit secret keys to version control**
- Store in environment variables or secure vaults
- Regenerate if compromised (requires database update)

### 2. Set Appropriate Intervals

- **Daily tasks**: `expected_interval: 86400` (24 hours)
- **Hourly tasks**: `expected_interval: 3600` (1 hour)
- **Weekly tasks**: `expected_interval: 604800` (7 days)

### 3. Use Grace Periods

Allow time for delays:
- **Short tasks**: 10-15% of interval (e.g., 1 hour for daily tasks)
- **Long tasks**: 25-50% of interval (e.g., 6 hours for daily backups)

### 4. Include Metadata

Send useful information in push payload:
```json
{
  "status": "success",
  "duration_seconds": 1234,
  "items_processed": 5000,
  "warnings": []
}
```

### 5. Handle Failures Gracefully

```bash
# In your script
if ! ./critical-task.sh; then
    # Still send push, but with error status
    curl -X POST "$PUSH_URL" -d '{"status":"error","message":"Task failed"}'
    exit 1
fi

# Send success push
curl -X POST "$PUSH_URL" -d '{"status":"success"}'
```

### 6. Test Your Integration

```bash
# Test the push URL manually
curl -v -X POST "http://localhost:5000/api/push/5/SECRET_KEY" \
    -H "Content-Type: application/json" \
    -d '{"status": "test", "message": "Testing push"}'
```

---

## Troubleshooting

### Push Not Registering

**Check the URL is correct:**
```bash
curl -v http://localhost:5000/api/push/5/SECRET_KEY
```

Look for:
- 404: Wrong monitor ID
- 403: Wrong secret key
- 200: Success

**Verify monitor is enabled:**
```bash
# Check config.yaml
grep -A 5 "Daily Backup" config.yaml
```

### Monitor Still Shows DOWN

**Check next expected deadline:**
```bash
# Query database
sqlite3 data/uptime.db "SELECT last_push_at, next_expected_at FROM push_monitors WHERE monitor_id = 5;"
```

**View recent check results:**
```bash
sqlite3 data/uptime.db "SELECT timestamp, status, error_message FROM check_results WHERE monitor_id = 5 ORDER BY timestamp DESC LIMIT 5;"
```

### Secret Key Lost

If you lose the secret key, you'll need to regenerate it in the database:

```bash
# Generate new secret (use a secure method in production)
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update database
sqlite3 data/uptime.db "UPDATE push_monitors SET secret_key = '$NEW_SECRET' WHERE monitor_id = 5;"

echo "New secret: $NEW_SECRET"
```

---

## Security Considerations

### 1. Use HTTPS in Production

Push URLs contain secret keys. Always use HTTPS to prevent interception:
```
https://uptime.example.com/api/push/5/SECRET_KEY
```

Set up a reverse proxy (Nginx, Apache) with SSL certificates.

### 2. Restrict Network Access

If possible, limit push API access:
- Firewall rules
- VPN only
- IP whitelist in reverse proxy

### 3. Monitor the Monitor

Set up external monitoring to ensure your uptime monitor itself is operational.

### 4. Rotate Secrets Periodically

Consider rotating secret keys every 6-12 months for high-security environments.

---

## Advanced Usage

### Conditional Pushes

Only push on success:
```bash
if [ $BACKUP_STATUS -eq 0 ]; then
    curl -X POST "$PUSH_URL"
fi
```

### Retry Logic

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def send_push_with_retry(url, max_retries=3):
    session = requests.Session()
    retry = Retry(total=max_retries, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session.post(url, timeout=10)
```

### Multiple Push Monitors

For complex workflows, use multiple push monitors:

```yaml
monitors:
  - name: "Backup: Database"
    type: "push"
    config:
      expected_interval: 86400

  - name: "Backup: Files"
    type: "push"
    config:
      expected_interval: 86400

  - name: "Backup: Verification"
    type: "push"
    config:
      expected_interval: 86400
```

Push to each separately as tasks complete.

---

For more information, see [YAML_REFERENCE.md](YAML_REFERENCE.md) and [INSTALLATION.md](INSTALLATION.md).
