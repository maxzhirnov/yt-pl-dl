from __future__ import annotations

from collections.abc import Iterable

from yt_dlp import YoutubeDL

from yt_pl_dl.models import PlaylistVideo


def _normalize_entries(entries: Iterable[dict], include_archived: bool) -> list[PlaylistVideo]:
    videos: list[PlaylistVideo] = []

    for entry in entries:
        video_id = entry.get("id")
        title = entry.get("title")
        if not video_id or not title:
            continue

        availability = entry.get("availability")
        if not include_archived and availability in {"private", "premium_only", "subscriber_only"}:
            continue

        videos.append(
            PlaylistVideo(
                video_id=video_id,
                title=title,
                webpage_url=entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                upload_date=entry.get("upload_date"),
                channel=entry.get("channel") or entry.get("uploader"),
                is_live=bool(entry.get("is_live")),
                availability=availability,
            )
        )

    return videos


def fetch_playlist_videos(
    playlist_url: str,
    include_archived: bool = False,
    skip_cert_check: bool = False,
) -> list[PlaylistVideo]:
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "lazy_playlist": False,
        "nocheckcertificate": skip_cert_check,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries") if isinstance(info, dict) else None
    if not entries:
        return []

    return _normalize_entries(entries, include_archived=include_archived)
