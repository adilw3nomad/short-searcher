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


def test_build_report_rows_composite_ranks_by_blended_score(sample_video):
    conn = store.connect(":memory:")
    t1 = datetime(2026, 5, 29, 12, 0, 0)
    t2 = datetime(2026, 5, 30, 12, 0, 0)  # +24h
    # "slow" has tiny velocity but huge engagement; "fast" has big velocity, low engagement.
    store.upsert_videos(conn, [
        sample_video(video_id="fast", title="XRP explodes", views=1000, likes=1, comments=0),
        sample_video(video_id="slow", title="Bitcoin update", views=1000, likes=900, comments=0),
    ], captured_at=t1)
    store.upsert_videos(conn, [
        sample_video(video_id="fast", title="XRP explodes", views=9000, likes=1, comments=0),
        sample_video(video_id="slow", title="Bitcoin update", views=1100, likes=990, comments=0),
    ], captured_at=t2)
    rows = reports.build_report_rows(conn, sort="composite", now=date(2026, 5, 30))
    # velocity winner is "fast" (+8000/24h) but engagement winner is "slow" (~0.9).
    # Assert both rows are present and each carries a composite score in [0,1].
    ids = {r["video_id"] for r in rows}
    assert ids == {"fast", "slow"}
    for r in rows:
        assert 0.0 <= r["composite"] <= 1.0
    # rows are sorted by composite descending
    assert rows == sorted(rows, key=lambda r: r["composite"], reverse=True)
    # "slow" wins engagement (0.3 weight) but "fast" dominates velocity (0.5) + lifetime (0.2),
    # so "fast" should rank first despite lower engagement.
    assert rows[0]["video_id"] == "fast"


def test_build_brief_medians_across_multiple_shorts(sample_video):
    conn = store.connect(":memory:")
    t = datetime(2026, 5, 30, 12, 0, 0)
    store.upsert_videos(conn, [
        sample_video(video_id="x1", title="XRP pump", views=100, likes=10, comments=0),
        sample_video(video_id="x2", title="XRP dump", views=200, likes=40, comments=0),
        sample_video(video_id="x3", title="XRP news", views=300, likes=90, comments=0),
    ], captured_at=t)
    brief = reports.build_brief(conn, top=10, now=date(2026, 5, 30))
    xrp = {c["coin"]: c for c in brief["coins"]}["XRP"]
    assert xrp["short_count"] == 3
    assert xrp["total_views"] == 600
    assert xrp["median_views"] == 200            # median of 100,200,300
    # engagement rates: 0.10, 0.20, 0.30 -> median 0.20
    assert xrp["median_engagement"] == 0.2
    assert len(xrp["top_shorts"]) == 3
