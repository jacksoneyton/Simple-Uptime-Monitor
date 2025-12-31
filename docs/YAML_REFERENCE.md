# YAML Configuration Reference

Complete reference for configuring Simple Uptime Monitor via `config.yaml`.

## Table of Contents

- [Global Settings](#global-settings)
- [Notification Channels](#notification-channels)
- [Monitor Groups](#monitor-groups)
- [Monitor Types](#monitor-types)
  - [HTTP/HTTPS Monitor](#httphttps-monitor)
  - [TCP Monitor](#tcp-monitor)
  - [Ping Monitor](#ping-monitor)
  - [DNS Monitor](#dns-monitor)
  - [WebSocket Monitor](#websocket-monitor)
  - [Docker Monitor](#docker-monitor)
  - [Push Monitor](#push-monitor)
- [Environment Variables](#environment-variables)
- [Examples](#examples)

---

## Global Settings

The `global` section configures application-wide settings.

```yaml
global:
  default_interval: 60          # Default check interval in seconds
  database: "data/uptime.db"    # SQLite database path

  web:
    host: "0.0.0.0"            # Web server host (0.0.0.0 = all interfaces)
    port: 5000                  # Web server port
    secret_key: "random-key"    # Flask secret key (auto-generated if omitted)

  timezone: "America/New_York"  # Timezone for reporting

  retention:
    ping_history_days: 30       # Keep detailed check results for N days
    aggregate_after_days: 90    # Aggregate older data into daily stats
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_interval` | integer | 60 | Default seconds between checks (can be overridden per monitor) |
| `database` | string | "data/uptime.db" | Path to SQLite database file |
| `web.host` | string | "0.0.0.0" | Web server listening address |
| `web.port` | integer | 5000 | Web server port |
| `web.secret_key` | string | auto | Flask session secret (leave blank for auto-generation) |
| `timezone` | string | "UTC" | IANA timezone for timestamps |
| `retention.ping_history_days` | integer | 30 | Days to keep detailed check data |
| `retention.aggregate_after_days` | integer | 90 | Days before aggregating to daily stats |

---

## Notification Channels

Define notification channels in the `notifications` section. Monitors reference these by name.

### Email (SMTP)

```yaml
notifications:
  - name: "admin_email"
    type: "email"
    enabled: true
    config:
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      smtp_user: "alerts@example.com"
      smtp_password: "${SMTP_PASSWORD}"  # From .env file
      smtp_use_tls: true
      from_address: "alerts@example.com"
      to_addresses:
        - "admin@example.com"
        - "team@example.com"
```

**Email Fields:**
- `smtp_host`: SMTP server hostname
- `smtp_port`: SMTP server port (587 for TLS, 465 for SSL, 25 for plain)
- `smtp_user`: SMTP username
- `smtp_password`: SMTP password (use environment variable)
- `smtp_use_tls`: Use STARTTLS encryption (true/false)
- `from_address`: Sender email address
- `to_addresses`: List of recipient email addresses

### Discord Webhook

```yaml
notifications:
  - name: "discord_alerts"
    type: "discord"
    enabled: true
    config:
      webhook_url: "${DISCORD_WEBHOOK_URL}"
      username: "Uptime Monitor"
      mention_role_id: "123456789"  # Optional: role ID to @mention
```

**Discord Fields:**
- `webhook_url`: Discord webhook URL (use environment variable)
- `username`: Bot username (optional)
- `mention_role_id`: Discord role ID to mention on DOWN events (optional)

### Slack Webhook

```yaml
notifications:
  - name: "slack_alerts"
    type: "slack"
    enabled: true
    config:
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#alerts"
      username: "Uptime Bot"
```

**Slack Fields:**
- `webhook_url`: Slack webhook URL (use environment variable)
- `channel`: Target channel (optional, webhook default used if omitted)
- `username`: Bot username (optional)

---

## Monitor Groups

Groups organize monitors on the dashboard.

```yaml
groups:
  - name: "Production Services"
    description: "Critical production infrastructure"
    display_order: 1

  - name: "Development"
    description: "Dev environment monitors"
    display_order: 2
```

**Fields:**
- `name`: Group name (referenced by monitors)
- `description`: Human-readable description
- `display_order`: Sort order on dashboard (lower numbers first)

---

## Monitor Types

All monitors share common fields:

```yaml
monitors:
  - name: "Monitor Name"        # Required: unique monitor name
    type: "http"                 # Required: monitor type
    enabled: true                # Optional: enable/disable (default: true)
    group: "Group Name"          # Optional: group assignment
    interval: 60                 # Optional: check interval in seconds
    timeout: 10                  # Optional: check timeout in seconds
    retry_count: 3               # Optional: number of retries on failure
    retry_delay: 5               # Optional: delay between retries in seconds
    config: {...}                # Required: type-specific configuration
    notifications: [...]         # Optional: notification channel names
    alert_on: [...]              # Optional: events to trigger alerts
```

### Common Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Unique monitor identifier |
| `type` | string | Yes | - | Monitor type (http, tcp, ping, dns, websocket, docker, push) |
| `enabled` | boolean | No | true | Enable or disable this monitor |
| `group` | string | No | "Ungrouped" | Group name for dashboard organization |
| `interval` | integer | No | global default | Seconds between checks |
| `timeout` | integer | No | 10 | Seconds before check times out |
| `retry_count` | integer | No | 1 | Number of retry attempts on failure |
| `retry_delay` | integer | No | 5 | Seconds between retry attempts |
| `config` | object | Yes | - | Monitor-specific configuration |
| `notifications` | list | No | [] | Notification channel names to alert |
| `alert_on` | list | No | ["down", "up"] | Events triggering alerts: down, up, ssl_expire, degraded |

---

## HTTP/HTTPS Monitor

Monitor web services with optional keyword/JSON validation and SSL certificate checking.

### Basic Example

```yaml
- name: "Website"
  type: "http"
  enabled: true
  interval: 30
  config:
    url: "https://example.com"
    method: "GET"
    expected_status_codes: [200, 201]
    follow_redirects: true
    verify_ssl: true
```

### With Custom Headers

```yaml
- name: "API Endpoint"
  type: "http"
  config:
    url: "https://api.example.com/status"
    method: "GET"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      User-Agent: "UptimeMonitor/1.0"
    expected_status_codes: [200]
```

### With Keyword Validation

```yaml
- name: "Blog Check"
  type: "http"
  config:
    url: "https://blog.example.com"
    keyword:
      search_for: "Welcome"
      regex: false         # Plain string search (true for regex)
      invert: false        # Fail if keyword IS found (for error pages)
```

### With JSON Validation

```yaml
- name: "API Health"
  type: "http"
  config:
    url: "https://api.example.com/health"
    json_query:
      path: "$.status"            # JSONPath expression
      expected_value: "healthy"   # Expected value
      # OR just check existence:
      # exists: true
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | Target URL |
| `method` | string | No | "GET" | HTTP method (GET, POST, PUT, DELETE, etc.) |
| `expected_status_codes` | list | No | [200] | Acceptable HTTP status codes |
| `headers` | object | No | {} | Custom HTTP headers |
| `body` | string | No | - | Request body (for POST/PUT) |
| `follow_redirects` | boolean | No | true | Follow HTTP redirects |
| `verify_ssl` | boolean | No | true | Verify SSL certificates |
| `keyword.search_for` | string | No | - | Text/regex to search for in response |
| `keyword.regex` | boolean | No | false | Use regex matching |
| `keyword.invert` | boolean | No | false | Fail if keyword IS found |
| `json_query.path` | string | No | - | JSONPath expression |
| `json_query.expected_value` | any | No | - | Expected value at path |
| `json_query.exists` | boolean | No | false | Only check if path exists |

---

## TCP Monitor

Test TCP port connectivity.

### Example

```yaml
- name: "Database"
  type: "tcp"
  config:
    host: "db.example.com"
    port: 5432
```

### Config Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | Hostname or IP address |
| `port` | integer | Yes | TCP port number |

---

## Ping Monitor

ICMP ping monitoring.

### Example

```yaml
- name: "Server Ping"
  type: "ping"
  config:
    host: "server.example.com"
    packet_count: 3
    packet_size: 56
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `host` | string | Yes | - | Hostname or IP address |
| `packet_count` | integer | No | 3 | Number of ICMP packets to send |
| `packet_size` | integer | No | 56 | Packet size in bytes |

---

## DNS Monitor

Validate DNS resolution.

### A Record Example

```yaml
- name: "DNS A Record"
  type: "dns"
  config:
    hostname: "example.com"
    resolver: "8.8.8.8"
    record_type: "A"
    expected_values:
      - "192.0.2.1"
      - "192.0.2.2"
    match_mode: "any"  # any, all, or exact
```

### MX Record Example

```yaml
- name: "Mail Server DNS"
  type: "dns"
  config:
    hostname: "example.com"
    resolver: "1.1.1.1"
    record_type: "MX"
    expected_contains: "mail.example.com"
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `hostname` | string | Yes | - | Domain to query |
| `resolver` | string | No | "8.8.8.8" | DNS server to use |
| `record_type` | string | No | "A" | Record type (A, AAAA, MX, TXT, CNAME, NS, etc.) |
| `expected_values` | list | No | - | List of expected values |
| `expected_contains` | string | No | - | Check if any result contains this string |
| `match_mode` | string | No | "any" | Validation mode: "any", "all", or "exact" |

**Match Modes:**
- `any`: At least one expected value must be present
- `all`: All expected values must be present
- `exact`: Results must exactly match expected values

---

## WebSocket Monitor

Monitor WebSocket connections.

### Basic Example

```yaml
- name: "WebSocket Server"
  type: "websocket"
  config:
    url: "wss://ws.example.com/socket"
```

### With Message Exchange

```yaml
- name: "WS with Handshake"
  type: "websocket"
  config:
    url: "wss://ws.example.com/socket"
    send_message: '{"type": "ping"}'
    expect_response: '{"type": "pong"}'
    response_timeout: 5
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | WebSocket URL (ws:// or wss://) |
| `send_message` | string | No | - | Message to send after connection |
| `expect_response` | string | No | - | Expected response substring |
| `response_timeout` | integer | No | 5 | Seconds to wait for response |

---

## Docker Monitor

Monitor Docker container health.

### Example

```yaml
- name: "Nginx Container"
  type: "docker"
  config:
    socket: "/var/run/docker.sock"
    container_name: "nginx-proxy"
    expect_status: "running"
    check_health: true
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `socket` | string | No | "/var/run/docker.sock" | Docker socket path or tcp://host:2375 |
| `container_name` | string | Yes* | - | Container name |
| `container_id` | string | Yes* | - | Container ID |
| `expect_status` | string | No | "running" | Expected container status |
| `check_health` | boolean | No | false | Use Docker HEALTHCHECK if configured |

*Either `container_name` or `container_id` must be specified.

---

## Push Monitor

Passive monitoring - external services push status updates.

### Example

```yaml
- name: "Backup Job"
  type: "push"
  config:
    expected_interval: 86400  # 24 hours
    grace_period: 3600        # 1 hour grace
    require_payload: false
```

### Config Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `expected_interval` | integer | Yes | - | Expected seconds between pushes |
| `grace_period` | integer | No | 0 | Additional grace period in seconds |
| `require_payload` | boolean | No | false | Require status payload in push |

### Push API Usage

After creating a push monitor, access the API at:

```
POST/GET http://your-server:5000/api/push/<monitor_id>/<secret_key>
```

The secret key is auto-generated and displayed in monitor metadata.

See [API.md](API.md) for details.

---

## Environment Variables

Use `${VAR_NAME}` syntax to substitute environment variables from `.env` file or shell environment.

### Example

**config.yaml:**
```yaml
notifications:
  - name: "email"
    config:
      smtp_password: "${SMTP_PASSWORD}"
```

**.env:**
```bash
SMTP_PASSWORD=my_secret_password
```

### Benefits

- Keep secrets out of version control
- Different values per environment
- Secure credential management

---

## Examples

### Complete Production Setup

```yaml
global:
  default_interval: 60
  database: "data/uptime.db"
  web:
    host: "0.0.0.0"
    port: 5000
  timezone: "America/New_York"

notifications:
  - name: "ops_email"
    type: "email"
    enabled: true
    config:
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      smtp_user: "ops@company.com"
      smtp_password: "${SMTP_PASSWORD}"
      smtp_use_tls: true
      from_address: "ops@company.com"
      to_addresses: ["oncall@company.com"]

  - name: "ops_discord"
    type: "discord"
    enabled: true
    config:
      webhook_url: "${DISCORD_WEBHOOK}"
      username: "Uptime Monitor"

groups:
  - name: "Web Services"
    display_order: 1

monitors:
  - name: "Main Website"
    type: "http"
    enabled: true
    group: "Web Services"
    interval: 30
    timeout: 10
    retry_count: 3
    config:
      url: "https://www.company.com"
      expected_status_codes: [200]
      verify_ssl: true
    notifications: ["ops_email", "ops_discord"]
    alert_on: ["down", "up", "ssl_expire"]

  - name: "Database Server"
    type: "tcp"
    enabled: true
    group: "Infrastructure"
    interval: 60
    config:
      host: "db.company.internal"
      port: 5432
    notifications: ["ops_email"]
    alert_on: ["down", "up"]
```

---

## Validation

Configuration is validated on startup. Common errors:

- **Missing required fields**: Ensure all required fields are present
- **Invalid monitor type**: Use supported types only
- **Duplicate monitor names**: Each monitor needs a unique name
- **Unknown notification channel**: Monitors can only reference defined notification channels
- **Environment variable not found**: Check `.env` file or environment

Run validation:

```bash
python3 -c "from uptime_monitor.config import load_config; load_config('config.yaml')"
```

---

## Best Practices

1. **Use environment variables** for all secrets
2. **Set appropriate intervals**: 30-60s for critical services, 300s+ for external APIs
3. **Configure timeouts** less than intervals
4. **Group related monitors** for better dashboard organization
5. **Test notification channels** before relying on them
6. **Monitor SSL expiration** for HTTPS endpoints
7. **Use retry_count=3** for network-based checks to avoid false positives
8. **Document your config** with YAML comments for team understanding

---

For more examples, see `config.example.yaml` in the project root.
