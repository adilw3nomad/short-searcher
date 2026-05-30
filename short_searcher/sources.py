import json
import logging
import subprocess
from datetime import date, datetime
from typing import Callable

from .models import Video

log = logging.getLogger("short_searcher.sources")
SHORT_MAX_SEC = 60


def _parse_duration(text: int | str) -> int:
    parts = [int(p) for p in str(text).split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _enrich(url: str) -> dict:
    out = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-warnings", url],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return json.loads(out.stdout)


def _default_client():  # pragma: no cover - thin wrapper over the library
    from tubescrape import YouTube
    return YouTube()


def _collect(results, enrich: Callable[[str], dict]) -> list[Video]:
    videos: list[Video] = []
    for r in results:
        try:
            if _parse_duration(r.duration) > SHORT_MAX_SEC:
                continue
            meta = enrich(r.url)
        except Exception as exc:  # noqa: BLE001 - skip the bad video, keep going
            log.warning("skipping %s: %s", getattr(r, "url", "?"), exc)
            continue
        videos.append(Video(
            video_id=meta["id"],
            title=meta.get("title", r.title),
            channel=meta.get("channel", getattr(r, "channel", "")),
            channel_id=meta.get("channel_id", ""),
            duration_sec=int(meta.get("duration", _parse_duration(r.duration))),
            published_at=datetime.strptime(meta["upload_date"], "%Y%m%d").date(),
            url=meta.get("webpage_url", r.url),
            views=int(meta.get("view_count") or 0),
            likes=int(meta.get("like_count") or 0),
            comments=int(meta.get("comment_count") or 0),
        ))
    return videos


def search_keyword(keyword: str, max_results: int = 50,
                   client_factory: Callable = _default_client,
                   enrich: Callable[[str], dict] = _enrich) -> list[Video]:
    with client_factory() as yt:
        response = yt.search(keyword, max_results=max_results)
    return _collect(response.videos, enrich)


def scan_channel(channel: str, max_results: int = 50,
                 client_factory: Callable = _default_client,
                 enrich: Callable[[str], dict] = _enrich) -> list[Video]:
    with client_factory() as yt:
        response = yt.get_channel_videos(channel, max_results=max_results)
    return _collect(response.videos, enrich)
