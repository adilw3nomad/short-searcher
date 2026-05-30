import sqlite3
from datetime import date, datetime
from pathlib import Path

from .models import Video

_SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT, channel TEXT, channel_id TEXT,
    duration_sec INTEGER, published_at TEXT, url TEXT,
    first_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT REFERENCES videos(video_id),
    captured_at TEXT, views INTEGER, likes INTEGER, comments INTEGER
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def upsert_videos(conn: sqlite3.Connection, videos: list[Video],
                  captured_at: datetime | None = None) -> None:
    captured_at = captured_at or datetime.now()
    ts = captured_at.isoformat()
    for v in videos:
        conn.execute(
            """INSERT INTO videos
               (video_id, title, channel, channel_id, duration_sec,
                published_at, url, first_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(video_id) DO UPDATE SET
                 title=excluded.title, channel=excluded.channel""",
            (v.video_id, v.title, v.channel, v.channel_id, v.duration_sec,
             v.published_at.isoformat(), v.url, ts),
        )
        conn.execute(
            """INSERT INTO snapshots (video_id, captured_at, views, likes, comments)
               VALUES (?, ?, ?, ?, ?)""",
            (v.video_id, ts, v.views, v.likes, v.comments),
        )
    conn.commit()


def latest_rows(conn: sqlite3.Connection, since_days: int | None = None,
                now: date | None = None) -> list[dict]:
    sql = """
        SELECT v.video_id, v.title, v.channel, v.duration_sec, v.published_at,
               v.url, s.views, s.likes, s.comments, s.captured_at
        FROM videos v
        JOIN snapshots s ON s.video_id = v.video_id
        WHERE s.id = (
            SELECT id FROM snapshots s2 WHERE s2.video_id = v.video_id
            ORDER BY captured_at DESC, id DESC LIMIT 1
        )
    """
    params: list = []
    if since_days is not None:
        now = now or date.today()
        cutoff = now.fromordinal(now.toordinal() - since_days).isoformat()
        sql += " AND v.published_at >= ?"
        params.append(cutoff)
    return [dict(r) for r in conn.execute(sql, params)]


def previous_views(conn: sqlite3.Connection) -> dict[str, int]:
    sql = """
        SELECT video_id, views FROM snapshots s
        WHERE id = (
            SELECT id FROM snapshots s2 WHERE s2.video_id = s.video_id
            ORDER BY captured_at DESC, id DESC LIMIT 1 OFFSET 1
        )
    """
    return {r["video_id"]: r["views"] for r in conn.execute(sql)}
