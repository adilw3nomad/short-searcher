from datetime import date, datetime
from statistics import median

from . import metrics, store
from .coins import COIN_MAP, extract_coins

_SORT_KEYS = {
    "velocity": "recent_velocity",
    "engagement": "engagement",
    "composite": "composite",
    "views": "views",
}


def _enrich_rows(conn, since_days=None, now=None) -> list[dict]:
    now = now or date.today()
    rows = store.latest_rows(conn, since_days=since_days, now=now)
    prev = store.previous_views(conn)
    for r in rows:
        r["published_at"] = date.fromisoformat(r["published_at"])
        # Real elapsed time between this video's two most recent snapshots.
        prev_entry = prev.get(r["video_id"])
        if prev_entry is not None:
            prev_views, prev_captured = prev_entry
            gap_hours = (datetime.fromisoformat(r["captured_at"])
                         - datetime.fromisoformat(prev_captured)).total_seconds() / 3600
        else:
            prev_views, gap_hours = None, 0.0
        r["engagement"] = metrics.engagement_rate(r["views"], r["likes"], r["comments"])
        r["lifetime_velocity"] = metrics.lifetime_velocity(r["views"], r["published_at"], now)
        r["recent_velocity"] = metrics.recent_velocity(r["views"], prev_views, gap_hours)
    triples = [(r["recent_velocity"], r["engagement"], r["lifetime_velocity"]) for r in rows]
    for r, score in zip(rows, metrics.composite_scores(triples)):
        r["composite"] = score
    return rows


def build_report_rows(conn, sort: str = "composite", since_days: int | None = None,
                      limit: int | None = None, now: date | None = None) -> list[dict]:
    rows = _enrich_rows(conn, since_days=since_days, now=now)
    key = _SORT_KEYS.get(sort, "composite")
    rows.sort(key=lambda r: r[key], reverse=True)
    return rows[:limit] if limit else rows


def build_brief(conn, since_days: int | None = None, top: int = 10,
                now: date | None = None) -> dict:
    rows = _enrich_rows(conn, since_days=since_days, now=now)
    by_coin: dict[str, list[dict]] = {}
    for r in rows:
        for ticker in extract_coins(r["title"], ""):
            by_coin.setdefault(ticker, []).append(r)

    coins = []
    for ticker, crows in by_coin.items():
        crows.sort(key=lambda r: r["recent_velocity"], reverse=True)
        coins.append({
            "coin": ticker,
            "name": COIN_MAP[ticker],
            "short_count": len(crows),
            "total_views": sum(r["views"] for r in crows),
            "median_views": int(median(r["views"] for r in crows)),
            "median_engagement": round(median(r["engagement"] for r in crows), 4),
            "median_recent_velocity": round(median(r["recent_velocity"] for r in crows), 2),
            "top_shorts": [
                {"title": r["title"], "url": r["url"], "views": r["views"],
                 "engagement": round(r["engagement"], 4),
                 "recent_velocity": round(r["recent_velocity"], 2)}
                for r in crows[:5]
            ],
        })
    coins.sort(key=lambda c: c["median_recent_velocity"], reverse=True)
    return {
        "generated_at": (now or date.today()).isoformat(),
        "window_days": since_days,
        "coins": coins[:top],
    }
