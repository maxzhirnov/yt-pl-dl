# Proxmox Deployment

## Recommended Approach

Для первого production deployment на Proxmox рекомендован такой вариант:

1. Поднять отдельный Linux VM или LXC container.
2. Установить Docker и Docker Compose plugin.
3. Склонировать репозиторий.
4. Примонтировать Synology share на host или прокинуть mount в LXC.
5. Скопировать `.env.production.example` в `.env.production`.
6. Настроить `SYNC_TARGET` на mounted path.
7. Запускать контейнер по cron или systemd timer на хосте.

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
docker compose pull
docker compose run --rm yt-pl-dl
```

## Scheduling Options

### Option 1: host cron

```cron
*/15 * * * * cd /opt/yt-pl-dl && docker compose run --rm yt-pl-dl >> /opt/yt-pl-dl/logs/cron.log 2>&1
```

### Option 2: systemd timer on host

Можно запускать `docker compose run --rm yt-pl-dl` из systemd unit на Proxmox host или внутри VM.

## Synology Integration

Когда сервис окажется в той же локальной сети:

- если папка NAS смонтирована на production host или прокинута в LXC, использовать `SYNC_MODE=copy`;
- если удобнее пушить по SSH, использовать `SYNC_MODE=rsync`.

Важно:

- `SYNC_TARGET` должен уже существовать;
- сервис специально не создает target directory в `copy` mode, чтобы не скрывать потерянный mount.
