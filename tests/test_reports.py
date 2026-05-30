from datetime import date, datetime
from short_searcher import store, reports


def _seed(conn, sample_video):
    t1 = datetime(2026, 5, 29, 12, 0, 0)
    t2 = datetime(2026, 5, 30, 12, 0, 0)   # +24h
    store.upsert_videos(conn, [
        sample_video(video_id="a", title="XRP explodes", views=1000),
        sample_video(video_id="b", title="Bitcoin to 100k", views=500),
    ], captured_at=t1)
    store.upsert_videos(conn, [
        sample_video(video_id="a", title="XRP explodes", views=3400),
        sample_video(video_id="b", title="Bitcoin to 100k", views=560),
    ], captured_at=t2)


def test_build_report_rows_sorted_by_velocity(sample_video):
    conn = store.connect(":memory:")
    _seed(conn, sample_video)
    rows = reports.build_report_rows(conn, sort="velocity", now=date(2026, 5, 30))
    assert [r["video_id"] for r in rows] == ["a", "b"]   # a grew faster
    assert rows[0]["recent_velocity"] == 100.0           # +2400 / 24h


def test_build_report_rows_limit(sample_video):
    conn = store.connect(":memory:")
    _seed(conn, sample_video)
    rows = reports.build_report_rows(conn, sort="views", limit=1)
    assert len(rows) == 1
    assert rows[0]["video_id"] == "a"


def test_build_brief_groups_by_coin(sample_video):
    conn = store.connect(":memory:")
    _seed(conn, sample_video)
    brief = reports.build_brief(conn, top=10, now=date(2026, 5, 30))
    coins = {c["coin"]: c for c in brief["coins"]}
    assert set(coins) == {"XRP", "BTC"}
    assert coins["XRP"]["short_count"] == 1
    assert coins["XRP"]["top_shorts"][0]["title"] == "XRP explodes"
    assert "total_views" in coins["XRP"]
