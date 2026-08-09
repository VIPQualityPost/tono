# Self-Hosting

tono can be self-hosted on any server with Python 3.10+ and Node.js 24+ (Node is only needed to build the frontend bundle; the packaged build ships `frontend/dist/` pre-built).

## Quick start

```bash
git clone https://github.com/VIPQualityPost/tono.git && cd tono
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"
cd frontend && npm ci && npm run build && cd ..
TONO_HOST=0.0.0.0 python -m backend.main
```

The server will be available at `http://<your-server-ip>:8188`.

## Running as a system service

To keep tono running in the background and auto-restart on reboot, create a systemd service.

### Create a service user

```bash
sudo useradd --system --create-home --shell /bin/false tono
sudo mkdir -p /var/lib/tono
sudo chown tono:tono /var/lib/tono
```

### Clone and install

```bash
sudo git clone https://github.com/VIPQualityPost/tono.git /opt/tono
sudo chown -R tono:tono /opt/tono
sudo -u tono bash -c 'cd /opt/tono && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[server]"'
sudo -u tono bash -c 'cd /opt/tono/frontend && npm ci && npm run build'
```

### Create the unit file

Save as `/etc/systemd/system/tono.service`:

```ini
[Unit]
Description=tono
After=network.target

[Service]
Type=simple
User=tono
WorkingDirectory=/opt/tono
ExecStart=/opt/tono/.venv/bin/python -m backend.main
Environment=TONO_HOST=127.0.0.1
Environment=TONO_PORT=8188
Environment=TONO_APPDATA=/var/lib/tono
Environment=TONO_UPDATE_CHECK=off
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable tono
sudo systemctl start tono
sudo systemctl status tono   # verify it's running
```

### Useful commands

```bash
sudo journalctl -u tono -f          # follow logs
sudo systemctl restart tono          # restart after updates
```

## HTTPS with Certbot

After setting up nginx (see [Reverse proxy](#reverse-proxy) below), use Certbot to get a free TLS certificate from Let's Encrypt.

### Install Certbot

```bash
# Ubuntu/Debian
sudo apt install nginx certbot python3-certbot-nginx
```

### Get a certificate

Point your domain's DNS A record at your server's IP, then:

```bash
sudo certbot --nginx -d tono.yourdomain.com
```

Certbot will automatically:
- Obtain a certificate
- Configure nginx to use it
- Set up auto-renewal (certificates renew every 90 days)

You can verify auto-renewal works with:

```bash
sudo certbot renew --dry-run
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `TONO_HOST` | `127.0.0.1` | Bind address. Set to `0.0.0.0` for remote access. |
| `TONO_PORT` | `8188` | Listen port. |
| `TONO_APPDATA` | Platform-dependent | Data directory for sessions and uploads. |
| `TONO_PLUGINS` | `0` (web mode) | Set to `1` to enable the plugin system. **Warning:** plugins execute arbitrary Python code. |
| `TONO_SESSION_TTL` | `60` | Seconds to wait after a user disconnects before cleaning up their session data. Set to `0` to disable cleanup. |
| `TONO_UPDATE_CHECK` | (enabled) | Set to `off` to disable the GitHub release update checker. The check compares the running build's git-tag version against the latest release. |

## Reverse proxy

You will almost certainly want to run tono behind a reverse proxy for TLS termination. The key requirement is proxying WebSocket connections on `/ws`.

### nginx

```nginx
server {
    listen 443 ssl;
    server_name tono.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8188;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        client_max_body_size 100M;
    }
}
```

### Caddy

```
tono.example.com {
    reverse_proxy localhost:8188
}
```

Caddy handles TLS, WebSocket upgrades, and headers automatically.

## Health check

`GET /health` returns `{"status": "ok"}` and can be used by load balancers or monitoring tools.

## Authentication

tono does not include built-in authentication. For access control, use your reverse proxy:

- **nginx**: HTTP basic auth (`auth_basic`) or integrate with an auth provider
- **Caddy**: `basicauth` directive or forward auth
- **Cloudflare Access**, **Authelia**, **Authentik**: external identity-aware proxies

## Session lifecycle

Each browser tab creates an isolated session with its own uploaded files, execution engine, and cache. When a user closes their tab (WebSocket disconnects) and does not reconnect within `TONO_SESSION_TTL` seconds, the server automatically cleans up:

- Execution engine and cached results
- Uploaded files on disk
- Pending downloads and rate limit state

Set `TONO_SESSION_TTL=0` to disable automatic cleanup (useful for single-user deployments).
