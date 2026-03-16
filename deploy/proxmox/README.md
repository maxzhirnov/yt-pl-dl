# Proxmox Deployment

## Recommended Approach

Для рабочего production deployment на Proxmox рекомендован такой вариант:

1. Поднять отдельный privileged LXC container.
2. Примонтировать Synology share на host и прокинуть его в LXC.
3. Установить Python, `ffmpeg`, `rsync`, `nodejs`, `npm`, `deno`, `tailscale`.
4. Подключить Tailscale exit node для доступа к YouTube.
5. Склонировать репозиторий.
6. Создать Python virtualenv и установить зависимости.
7. Настроить `cookies.txt`, `yt-dlp-ejs` и `bgutil-ytdlp-pot-provider`.
8. Скопировать `.env.production.example` в `.env.production`.
9. Запускать сервис через `systemd` timer.

## Recommended Sync Model

Предпочтительный production-вариант:

1. Synology share монтируется как обычная директория.
2. Приложение видит ее как локальный путь.
3. Сервис работает в `SYNC_MODE=copy`.

Это проще и надежнее, чем встраивать сетевую логику Synology внутрь самого приложения.

## First Run

```bash
cp .env.production.example .env.production
mkdir -p data logs
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m yt_pl_dl.main run-once
```

## Scheduling Options

### Option 1: systemd timer inside LXC

Использовать [bgutil-pot-provider.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/bgutil-pot-provider.service), [yt-pl-dl.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.service) и [yt-pl-dl.timer](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl.timer).

### Option 2: host cron

Возможен, но `systemd` внутри LXC предпочтительнее.

## Synology Integration

Когда сервис окажется в той же локальной сети:

- если папка NAS смонтирована на production host или прокинута в LXC, использовать `SYNC_MODE=copy`;
- если удобнее пушить по SSH, использовать `SYNC_MODE=rsync`.

Важно:

- `SYNC_TARGET` должен уже существовать;
- сервис специально не создает target directory в `copy` mode, чтобы не скрывать потерянный mount.
