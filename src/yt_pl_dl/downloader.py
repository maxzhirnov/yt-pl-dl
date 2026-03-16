from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL

from yt_pl_dl.config import Settings
from yt_pl_dl.models import PlaylistVideo


@dataclass(slots=True)
class DownloadResult:
    file_path: Path
    format_id: str | None
    ext: str | None
    width: int | None
    height: int | None
    vcodec: str | None
    acodec: str | None


def _preferred_format(max_height: int) -> str:
    # Prefer the best quality up to the configured height without overfitting to
    # specific codec labels that may vary per video/account/region.
    return (
        f"(bestvideo*[height<={max_height}]+bestaudio/best*[height<={max_height}])/"
        "bestvideo*+bestaudio/best"
    )


def _extract_download_result(info: dict, fallback_path: str | None) -> DownloadResult:
    requested_formats = info.get("requested_formats") or []
    requested_downloads = info.get("requested_downloads") or []

    video_stream = next((item for item in requested_formats if item.get("vcodec") not in {None, "none"}), None)
    audio_stream = next((item for item in requested_formats if item.get("acodec") not in {None, "none"}), None)

    file_path = None
    if requested_downloads:
        file_path = requested_downloads[0].get("filepath")
    if not file_path:
        file_path = fallback_path or info.get("_filename")
    if not file_path:
        raise RuntimeError(f"Unable to determine downloaded file path for video {info.get('id')}")

    return DownloadResult(
        file_path=Path(file_path),
        format_id=info.get("format_id"),
        ext=info.get("ext"),
        width=info.get("width") or (video_stream or {}).get("width"),
        height=info.get("height") or (video_stream or {}).get("height"),
        vcodec=info.get("vcodec") or (video_stream or {}).get("vcodec"),
        acodec=info.get("acodec") or (audio_stream or {}).get("acodec"),
    )


def download_video(video: PlaylistVideo, settings: Settings) -> DownloadResult:
    download_dir = settings.local_download_dir
    download_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": _preferred_format(settings.download_max_height),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": settings.yt_skip_cert_check,
        "paths": {"home": str(download_dir)},
        "outtmpl": {
            "default": "%(upload_date)s - %(title)s [%(id)s].%(ext)s",
        },
    }
    if settings.yt_cookies_path:
        ydl_opts["cookiefile"] = str(settings.yt_cookies_path)

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video.webpage_url, download=True)
        prepared_filename = ydl.prepare_filename(info)

    return _extract_download_result(info, fallback_path=prepared_filename)
