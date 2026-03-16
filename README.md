# yt-pl-dl

Python service for monitoring a YouTube playlist, identifying new videos, and preparing them for download and sync to Synology DSM.

## Current status

Implemented in this iteration:

- config loading from environment;
- playlist metadata fetch through `yt-dlp`;
- local state storage in `sqlite`;
- CLI command to inspect the playlist and show which videos are new;
- one-shot workflow to check, download, and sync new videos;
- file logging for operational runs;
- working production deployment path for Proxmox LXC via Python venv + systemd timer.

Still not implemented:

- scheduler/daemon mode;
- notifications;
- richer retry policy and observability.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Usage

Check playlist and print unseen videos:

```bash
PYTHONPATH=src python3 -m yt_pl_dl.main check
```

Run the whole workflow once:

```bash
PYTHONPATH=src python3 -m yt_pl_dl.main run-once
```

Show already tracked videos:

```bash
PYTHONPATH=src python3 -m yt_pl_dl.main state
```

Bootstrap local state from the current playlist without downloading:

```bash
PYTHONPATH=src python3 -m yt_pl_dl.main bootstrap-state --yes
```

## Notes

- `yt-dlp` must be able to access YouTube from the machine where the script runs.
- If local Python has broken CA certificates, set `YT_SKIP_CERT_CHECK=1` as a temporary workaround.
- If YouTube requires bot verification, provide `YT_COOKIES_PATH` pointing to an exported `cookies.txt`.
- By default downloads now prefer QuickTime-friendly `mp4/h264+aac` and cap video at `1080p`. Override with `DOWNLOAD_MAX_HEIGHT`.
- Logs are written to `./logs/yt-pl-dl.log` by default.
- Recommended production mode is `SYNC_MODE=copy` with a mounted Synology directory exposed into the host/LXC/container.
- `SYNC_MODE=copy` expects `SYNC_TARGET` to already exist; the service will fail if the mounted path is missing.
- `SYNC_MODE=rsync` expects `SYNC_TARGET` in `rsync` format, for example `user@192.168.1.10:/volume1/media/youtube`.

## Deployment

Recommended production deployment:

- Proxmox LXC
- Python virtualenv
- `systemd` timer for periodic runs
- mounted Synology path with `SYNC_MODE=copy`
- Tailscale exit node for YouTube access
- `cookies.txt` + `yt-dlp-ejs` + `deno` + `bgutil-ytdlp-pot-provider` for YouTube anti-bot handling

Deployment files:

- [.env.production.example](/Users/mzhirnov/Documents/github/yt-pl-dl/.env.production.example) as the production config template;
- [deploy/proxmox/README.md](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/proxmox/README.md) for the suggested Proxmox workflow;
- [bgutil-pot-provider.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/bgutil-pot-provider.service) for the local PO token provider;
- [yt-pl-dl.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.service) and [yt-pl-dl.timer](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.timer) for systemd-based scheduling.

## GitHub Actions

Included workflows:

- `.github/workflows/ci.yml`: dependency install, compile check, CLI smoke test.

## Next Production Step

The intended Proxmox flow is:

```bash
cp .env.production.example .env.production
mkdir -p data logs secrets
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m yt_pl_dl.main run-once
```

Recommended production architecture:

- mount the Synology share on the Proxmox host or inside the LXC;
- use `SYNC_MODE=copy`;
- point `SYNC_TARGET` at the mounted path, for example `/mnt/media/youtube`.
- run the service directly in the LXC, not via Docker-in-LXC.
