# Proxmox Deployment

## Recommended Approach

Для первого production deployment на Proxmox рекомендован такой вариант:

1. Поднять отдельный Linux VM или LXC container.
2. Установить Docker и Docker Compose plugin.
3. Склонировать репозиторий.
4. Скопировать `.env.production.example` в `.env.production`.
5. Настроить `SYNC_MODE` и `SYNC_TARGET` под реальный доступ к Synology.
6. Запускать контейнер по cron или systemd timer на хосте.

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

- если папка NAS смонтирована на production host, использовать `SYNC_MODE=copy`;
- если удобнее пушить по SSH, использовать `SYNC_MODE=rsync`.
