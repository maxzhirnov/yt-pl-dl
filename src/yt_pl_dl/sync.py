from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from yt_pl_dl.config import Settings


def sync_file(file_path: Path, settings: Settings) -> None:
    if settings.sync_mode == "none":
        return

    if settings.sync_mode == "copy":
        if not settings.sync_target:
            raise ValueError("SYNC_TARGET is required when SYNC_MODE=copy")

        target_dir = Path(settings.sync_target).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_dir / file_path.name)
        return

    if settings.sync_mode == "rsync":
        if not settings.sync_target:
            raise ValueError("SYNC_TARGET is required when SYNC_MODE=rsync")

        subprocess.run(
            ["rsync", "-av", str(file_path), settings.sync_target],
            check=True,
        )
        return

    raise ValueError(f"Unsupported SYNC_MODE: {settings.sync_mode}")
