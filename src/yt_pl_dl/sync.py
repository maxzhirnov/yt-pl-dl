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
        if not target_dir.exists():
            raise FileNotFoundError(
                f"SYNC_TARGET does not exist for SYNC_MODE=copy: {target_dir}"
            )
        if not target_dir.is_dir():
            raise NotADirectoryError(
                f"SYNC_TARGET is not a directory for SYNC_MODE=copy: {target_dir}"
            )

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
