# Self-Hosting

tono can be self-hosted on any server with Python 3.10+ and Node.js 18+.

## Quick start

```bash
git clone https://github.com/VIPQualityPost/tono.git && cd tono
python -m venv .venv && source .venv/bin/activate
pip install -e .
cd frontend && npm ci && npm run build && cd ..
TONO_HOST=0.0.0.0 tono
```

The server will be available at `http://<your-server-ip>:8188`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `TONO_HOST` | `127.0.0.1` | Bind address. Set to `0.0.0.0` for remote access. |
| `TONO_PORT` | `8188` | Listen port. |
| `TONO_APPDATA` | Platform-dependent | Data directory for sessions and uploads. |
| `TONO_PLUGINS` | `0` (web mode) | Set to `1` to enable the plugin system. **Warning:** plugins execute arbitrary Python code. |
| `TONO_SESSION_TTL` | `60` | Seconds to wait after a user disconnects before cleaning up their session data. Set to `0` to disable cleanup. |
| `TONO_UPDATE_CHECK` | (enabled) | Set to `off` to disable the GitHub release update checker. |

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
