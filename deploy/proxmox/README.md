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
10. При необходимости поднять локальный dashboard и опубликовать его через Nginx Proxy Manager.

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

Пример установки внутри LXC:

```bash
cd /opt/yt-pl-dl
cp .env.production .env
cp deploy/systemd/bgutil-pot-provider.service /etc/systemd/system/
cp deploy/systemd/yt-pl-dl.service /etc/systemd/system/
cp deploy/systemd/yt-pl-dl.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tailscaled
systemctl enable --now bgutil-pot-provider.service
systemctl start yt-pl-dl.service
systemctl enable --now yt-pl-dl.timer
```

Проверка:

```bash
systemctl status bgutil-pot-provider.service --no-pager
systemctl status yt-pl-dl.service --no-pager
systemctl status yt-pl-dl.timer --no-pager
systemctl list-timers --all | grep yt-pl-dl
journalctl -u yt-pl-dl.service -n 100 --no-pager
```

### Option 2: dashboard service inside LXC

Для local UI использовать [yt-pl-dl-dashboard.service](/Users/mzhirnov/Documents/github/yt-pl-dl/deploy/systemd/yt-pl-dl-dashboard.service).

Рекомендуется:

- слушать только `127.0.0.1`;
- публиковать наружу через Nginx Proxy Manager;
- оставить Basic Auth включенным на уровне приложения.

### Option 2: host cron

Возможен, но `systemd` внутри LXC предпочтительнее.

## Synology Integration

Когда сервис окажется в той же локальной сети:

- если папка NAS смонтирована на production host или прокинута в LXC, использовать `SYNC_MODE=copy`;
- если удобнее пушить по SSH, использовать `SYNC_MODE=rsync`.

Важно:

- `SYNC_TARGET` должен уже существовать;
- сервис специально не создает target directory в `copy` mode, чтобы не скрывать потерянный mount.
