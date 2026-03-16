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
- deployment scaffolding for Proxmox via Docker or systemd timer.

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
- By default downloads now prefer QuickTime-friendly `mp4/h264+aac` and cap video at `1080p`. Override with `DOWNLOAD_MAX_HEIGHT`.
- Logs are written to `./logs/yt-pl-dl.log` by default.
- `SYNC_MODE=copy` expects `SYNC_TARGET` to be a local or mounted directory.
- `SYNC_MODE=rsync` expects `SYNC_TARGET` in `rsync` format, for example `user@192.168.1.10:/volume1/media/youtube`.

## Deployment

For Proxmox or another always-on host you can use:

- [Dockerfile](/Users/mzhirnov/Documents/github/yt-pl-dl/Dockerfile) for containerized runs;
- [yt-pl-dl.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.service) and [yt-pl-dl.timer](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.timer) for systemd-based scheduling.

## GitHub Actions

Included workflows:

- `.github/workflows/ci.yml`: dependency install, compile check, CLI smoke test;
- `.github/workflows/docker-publish.yml`: build and push Docker image to Docker Hub on `main` and version tags.

Required GitHub repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Expected Docker Hub image name:

- `DOCKERHUB_USERNAME/yt-pl-dl`
