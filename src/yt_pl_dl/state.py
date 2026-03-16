from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from yt_pl_dl.models import PlaylistVideo


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    webpage_url TEXT NOT NULL,
    upload_date TEXT,
    channel TEXT,
    local_path TEXT,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._ensure_local_path_column(conn)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def is_processed(self, video_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_videos WHERE video_id = ? LIMIT 1",
                (video_id,),
            ).fetchone()
        return row is not None

    def get_processed_ids(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT video_id FROM processed_videos").fetchall()
        return {row[0] for row in rows}

    def get_processed_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM processed_videos").fetchone()
        return int(row[0]) if row else 0

    def mark_processed(self, video: PlaylistVideo, local_path: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_videos (
                    video_id,
                    title,
                    webpage_url,
                    upload_date,
                    channel,
                    local_path
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    webpage_url = excluded.webpage_url,
                    upload_date = excluded.upload_date,
                    channel = excluded.channel,
                    local_path = excluded.local_path
                """,
                (
                    video.video_id,
                    video.title,
                    video.webpage_url,
                    video.upload_date,
                    video.channel,
                    local_path,
                ),
            )

    def list_processed(self) -> list[tuple[str, str, str | None, str | None, str | None]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT video_id, title, channel, discovered_at, local_path
                FROM processed_videos
                ORDER BY discovered_at DESC, video_id DESC
                """
            ).fetchall()
        return [(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    def get_processed_video(self, video_id: str) -> tuple[str, str, str | None, str | None, str | None] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT video_id, title, channel, discovered_at, local_path
                FROM processed_videos
                WHERE video_id = ?
                LIMIT 1
                """,
                (video_id,),
            ).fetchone()
        if not row:
            return None
        return (row[0], row[1], row[2], row[3], row[4])

    def clear_local_path(self, video_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE processed_videos SET local_path = NULL WHERE video_id = ?",
                (video_id,),
            )

    def _ensure_local_path_column(self, conn: sqlite3.Connection) -> None:
        columns = conn.execute("PRAGMA table_info(processed_videos)").fetchall()
        if any(column[1] == "local_path" for column in columns):
            return
        conn.execute("ALTER TABLE processed_videos ADD COLUMN local_path TEXT")
