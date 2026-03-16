from __future__ import annotations

import argparse
import logging
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-pl-dl",
        description="Monitor a YouTube playlist and track newly discovered videos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check playlist and print unseen videos.")
    subparsers.add_parser("run-once", help="Check playlist, download new videos, and sync them.")
    subparsers.add_parser("state", help="Show tracked videos from the local state database.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap-state",
        help="Mark current playlist videos as already processed without downloading them.",
    )
    bootstrap_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that current playlist items should be imported into local state.",
    )
    return parser


def _setup_runtime():
    from yt_pl_dl.config import load_settings
    from yt_pl_dl.logging_setup import configure_logging

    settings = load_settings()
    configure_logging(settings.log_file_path, settings.log_level)
    return settings


def cmd_check() -> int:
    from yt_pl_dl.config import load_playlist_url
    from yt_pl_dl.playlist import fetch_playlist_videos
    from yt_pl_dl.state import StateStore

    logger = logging.getLogger(__name__)
    settings = _setup_runtime()
    playlist_url = load_playlist_url()
    store = StateStore(settings.state_db_path)
    store.init_db()

    videos = fetch_playlist_videos(
        playlist_url,
        include_archived=settings.check_archived,
        skip_cert_check=settings.yt_skip_cert_check,
    )
    processed_ids = store.get_processed_ids()
    new_videos = [video for video in videos if video.video_id not in processed_ids]
    logger.info(
        "Playlist check completed: total=%s processed=%s new=%s",
        len(videos),
        len(processed_ids),
        len(new_videos),
    )

    if not new_videos:
        print("No new videos found.")
        return 0

    print(f"Found {len(new_videos)} new video(s):")
    for video in new_videos:
        channel = f" | channel={video.channel}" if video.channel else ""
        upload_date = f" | upload_date={video.upload_date}" if video.upload_date else ""
        print(f"- {video.title} [{video.video_id}]{channel}{upload_date}")
        print(f"  {video.webpage_url}")

    return 0


def cmd_state() -> int:
    from yt_pl_dl.state import StateStore

    logger = logging.getLogger(__name__)
    settings = _setup_runtime()
    store = StateStore(settings.state_db_path)
    store.init_db()

    rows = store.list_processed()
    if not rows:
        logger.info("State requested: empty")
        print("State is empty.")
        return 0

    logger.info("State requested: tracked=%s", len(rows))
    print(f"Tracked videos: {len(rows)}")
    for video_id, title, channel, discovered_at, local_path in rows:
        channel_part = f" | channel={channel}" if channel else ""
        path_part = f" | local_path={local_path}" if local_path else ""
        print(f"- {title} [{video_id}] | discovered_at={discovered_at}{channel_part}{path_part}")
    return 0


def cmd_bootstrap_state(confirm: bool) -> int:
    from yt_pl_dl.config import load_playlist_url
    from yt_pl_dl.playlist import fetch_playlist_videos
    from yt_pl_dl.state import StateStore

    logger = logging.getLogger(__name__)
    settings = _setup_runtime()
    if not confirm:
        logger.warning("Refused bootstrap-state without --yes")
        print("Refusing to modify state without --yes.")
        return 2

    playlist_url = load_playlist_url()
    store = StateStore(settings.state_db_path)
    store.init_db()

    videos = fetch_playlist_videos(
        playlist_url,
        include_archived=settings.check_archived,
        skip_cert_check=settings.yt_skip_cert_check,
    )

    if not videos:
        print("Playlist is empty.")
        return 0

    for video in videos:
        store.mark_processed(video)

    logger.warning("Bootstrapped state from current playlist: imported=%s", len(videos))
    print(f"Imported {len(videos)} current playlist video(s) into local state.")
    return 0


def cmd_run_once() -> int:
    from yt_pl_dl.config import load_playlist_url
    from yt_pl_dl.downloader import download_video
    from yt_pl_dl.playlist import fetch_playlist_videos
    from yt_pl_dl.state import StateStore
    from yt_pl_dl.sync import sync_file

    logger = logging.getLogger(__name__)
    settings = _setup_runtime()
    playlist_url = load_playlist_url()
    store = StateStore(settings.state_db_path)
    store.init_db()

    videos = fetch_playlist_videos(
        playlist_url,
        include_archived=settings.check_archived,
        skip_cert_check=settings.yt_skip_cert_check,
    )
    processed_ids = store.get_processed_ids()
    new_videos = [video for video in videos if video.video_id not in processed_ids]
    logger.info(
        "Run started: total=%s processed=%s new=%s sync_mode=%s",
        len(videos),
        len(processed_ids),
        len(new_videos),
        settings.sync_mode,
    )

    if not new_videos:
        print("No new videos found.")
        logger.info("Run finished with no new videos.")
        return 0

    print(f"Found {len(new_videos)} new video(s).")
    for index, video in enumerate(new_videos, start=1):
        print(f"[{index}/{len(new_videos)}] Downloading: {video.title} [{video.video_id}]")
        logger.info("Downloading video_id=%s title=%s", video.video_id, video.title)
        download_result = download_video(video, settings)
        quality = (
            f"{download_result.width}x{download_result.height}"
            if download_result.width and download_result.height
            else "unknown"
        )
        print(
            "Downloaded to: "
            f"{download_result.file_path} | quality={quality} | "
            f"vcodec={download_result.vcodec} | acodec={download_result.acodec}"
        )
        logger.info(
            "Download completed: video_id=%s file=%s quality=%s vcodec=%s acodec=%s",
            video.video_id,
            download_result.file_path,
            quality,
            download_result.vcodec,
            download_result.acodec,
        )

        if settings.sync_mode != "none":
            print(f"Syncing via mode={settings.sync_mode}")
            sync_file(download_result.file_path, settings)
            print("Sync completed.")
            logger.info(
                "Sync completed: video_id=%s file=%s mode=%s target=%s",
                video.video_id,
                download_result.file_path,
                settings.sync_mode,
                settings.sync_target,
            )

        store.mark_processed(video, local_path=str(download_result.file_path))
        print("Marked as processed.")
        logger.info("Marked processed: video_id=%s", video.video_id)

    logger.info("Run finished successfully: downloaded=%s", len(new_videos))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return cmd_check()
    if args.command == "bootstrap-state":
        return cmd_bootstrap_state(confirm=args.yes)
    if args.command == "run-once":
        return cmd_run_once()
    if args.command == "state":
        return cmd_state()

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
