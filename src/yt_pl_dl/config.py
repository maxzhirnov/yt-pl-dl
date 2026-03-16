from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional until dependencies are installed
    def load_dotenv() -> bool:
        return False


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    yt_skip_cert_check: bool
    download_max_height: int
    local_download_dir: Path
    state_db_path: Path
    log_file_path: Path
    log_level: str
    sync_mode: str
    sync_target: str
    check_archived: bool


def load_settings() -> Settings:
    load_dotenv()

    local_download_dir = Path(os.getenv("LOCAL_DOWNLOAD_DIR", "./data/downloads")).expanduser()
    state_db_path = Path(os.getenv("STATE_DB_PATH", "./data/state.db")).expanduser()
    download_max_height = int(os.getenv("DOWNLOAD_MAX_HEIGHT", "1080"))
    log_file_path = Path(os.getenv("LOG_FILE_PATH", "./logs/yt-pl-dl.log")).expanduser()

    return Settings(
        yt_skip_cert_check=_as_bool(os.getenv("YT_SKIP_CERT_CHECK"), default=False),
        download_max_height=download_max_height,
        local_download_dir=local_download_dir,
        state_db_path=state_db_path,
        log_file_path=log_file_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        sync_mode=os.getenv("SYNC_MODE", "none").strip().lower(),
        sync_target=os.getenv("SYNC_TARGET", "").strip(),
        check_archived=_as_bool(os.getenv("CHECK_ARCHIVED"), default=False),
    )


def load_playlist_url() -> str:
    load_dotenv()
    playlist_url = os.getenv("YT_PLAYLIST_URL", "").strip()
    if not playlist_url:
        raise ValueError("YT_PLAYLIST_URL is required")
    return playlist_url
