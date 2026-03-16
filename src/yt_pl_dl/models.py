from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlaylistVideo:
    video_id: str
    title: str
    webpage_url: str
    upload_date: str | None
    channel: str | None
    is_live: bool
    availability: str | None
