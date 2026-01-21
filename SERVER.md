# Production Server (nyx-cloud)

The Solara documentation website runs on the `nyx-cloud` server.

## Server Details

| Setting | Value |
|---------|-------|
| Host | `nyx-cloud` |
| Branch | `stable-ssg` |
| Working directory | `/root/solara` |
| Python | `/root/solara/.venv/bin/python3` (Python 3.12) |
| Port | 80 |

## Systemd Service

The server runs as a systemd service defined in `/etc/systemd/system/solara.service`:

```ini
[Unit]
Description=Solara Website
After=network.target

[Service]
User=root
WorkingDirectory=/root/solara
EnvironmentFile=/root/solara/solara.env
ExecStart=/root/solara/.venv/bin/solara run --host=0.0.0.0 --port=80 solara.website.pages --ssg --production
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Environment Variables

Environment variables are stored in `/root/solara/solara.env`:

- `SOLARA_MODE=production`
- `SOLARA_EXPERIMENTAL_PERFORMANCE=true`
- `UVICORN_PROXY_HEADERS=1`
- `FORWARDED_ALLOW_IPS=*`
- Various API keys for telemetry, email (Postmark), and OpenAI

## Common Commands

```bash
# Check service status
ssh nyx-cloud "systemctl status solara.service"

# View logs (live)
ssh nyx-cloud "journalctl -u solara.service -f"

# View recent logs
ssh nyx-cloud "journalctl -u solara.service -n 100"

# Restart the service
ssh nyx-cloud "systemctl restart solara.service"

# Check which version is deployed
ssh nyx-cloud "cd /root/solara && git log -1 --oneline"
```

## Updating the Server After a Release

After pushing to `stable` (which triggers SSG generation to `stable-ssg`), wait for CI to complete before updating the server:

```bash
# Wait for the webdeploy workflow to finish
gh run list --workflow=webdeploy.yml --limit=1
gh run watch <run-id>

# Pull latest changes and restart
ssh nyx-cloud "cd /root/solara && git pull && systemctl restart solara.service"
```

## Deployment Flow

1. Release is made on `master` branch
2. Push `master` to `stable`: `git push upstream master:stable`
3. CI runs `webdeploy.yml` workflow which generates SSG pages and pushes to `stable-ssg`
4. Wait for CI to complete: `gh run watch <run-id>`
5. Pull changes on nyx-cloud and restart the service
