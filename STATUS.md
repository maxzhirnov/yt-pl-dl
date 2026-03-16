# Status

## Current State

Проект находится на стадии рабочего MVP.

Что уже реализовано:

- проверка YouTube playlist через `yt-dlp`;
- определение новых видео по `video_id`;
- хранение состояния в `sqlite`;
- разовый запуск полного сценария: проверить playlist, скачать новые видео, отметить как обработанные;
- локальное сохранение файлов в `data/downloads`;
- файловое логирование в `logs/yt-pl-dl.log`;
- базовые режимы sync:
  - `none`
  - `copy`
  - `rsync`
- приоритет загрузки `1080p` или ниже;
- приоритет QuickTime-friendly формата: `mp4 + H.264 + AAC`;
- конфиг через `.env`;
- deployment-заготовки для Docker и systemd timer;
- базовые GitHub Actions workflow для CI и публикации Docker image;
- production-заготовки для запуска на Proxmox через Docker Compose.

## Verified

Подтверждено руками:

- `check` на реальном playlist работает;
- `state` показывает сохраненные записи;
- `run-once` скачивает файл локально;
- после корректировки формата файл открывается на macOS.

## Commands

Основные команды:

```bash
PYTHONPATH=src .venv/bin/python -m yt_pl_dl.main check
PYTHONPATH=src .venv/bin/python -m yt_pl_dl.main run-once
PYTHONPATH=src .venv/bin/python -m yt_pl_dl.main state
```

## Important Notes

- небезопасный сценарий `check --mark-seen` убран из основного CLI;
- вместо него есть явная служебная команда `bootstrap-state --yes`;
- основная команда для боевой работы сейчас: `run-once`;
- на этой машине может требоваться `YT_SKIP_CERT_CHECK=1` из-за локальной SSL-конфигурации Python.

## Next Steps

Ближайшие задачи:

1. Пока нет доступа к локальной сети, разрабатывать и тестировать сервис в режиме `SYNC_MODE=none` или `SYNC_MODE=copy`.
2. Проверить, что GitHub Actions действительно публикует image в Docker Hub.
3. После появления доступа к локальной сети подключить реальный sync на Synology.
4. Добавить запуск по расписанию на production host.
5. Добавить защиту от частично скачанных или неуспешно синхронизированных файлов.
6. Добавить более аккуратную обработку ошибок и retry.

## Development Workflow

Рекомендуемый workflow на текущем этапе:

1. Локально разрабатывать core-логику:
   - playlist check;
   - download;
   - state management;
   - идемпотентность;
   - логирование.
2. Sync-тесты пока делать только в режиме `copy` на локальную тестовую папку.
3. Отдельно подготовить production-конфиг для Proxmox.
4. После деплоя в локальную сеть включить `rsync` или запись в mounted Synology path.
5. Финальный end-to-end тест делать уже только на production host внутри локальной сети.

## Decisions

Зафиксированные решения:

- язык: Python;
- YouTube integration: `yt-dlp`;
- state storage: `sqlite`;
- основной сценарий: локальная загрузка -> sync на Synology -> Plex подхватывает из папки NAS.
