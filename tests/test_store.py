from datetime import date, datetime
from short_searcher import store


def test_upsert_inserts_video_and_snapshot(sample_video):
    conn = store.connect(":memory:")
    t = datetime(2026, 5, 30, 12, 0, 0)
    store.upsert_videos(conn, [sample_video(views=1000)], captured_at=t)
    rows = store.latest_rows(conn)
    assert len(rows) == 1
    assert rows[0]["views"] == 1000
    assert rows[0]["title"] == "XRP is about to explode"


def test_second_run_appends_snapshot_not_video(sample_video):
    conn = store.connect(":memory:")
    t1 = datetime(2026, 5, 30, 12, 0, 0)
    t2 = datetime(2026, 5, 31, 12, 0, 0)
    store.upsert_videos(conn, [sample_video(views=1000)], captured_at=t1)
    store.upsert_videos(conn, [sample_video(views=1500)], captured_at=t2)

    rows = store.latest_rows(conn)
    assert len(rows) == 1               # still one video
    assert rows[0]["views"] == 1500     # latest snapshot wins

    prev = store.previous_views(conn)
    assert prev["abc123"][0] == 1000       # prior snapshot views


def test_previous_views_empty_when_single_snapshot(sample_video):
    conn = store.connect(":memory:")
    store.upsert_videos(conn, [sample_video()], captured_at=datetime(2026, 5, 30))
    assert store.previous_views(conn) == {}


def test_latest_rows_since_filters_by_publish_date(sample_video):
    conn = store.connect(":memory:")
    t = datetime(2026, 5, 30, 12, 0, 0)
    store.upsert_videos(conn, [
        sample_video(video_id="new", published_at=date(2026, 5, 29)),
        sample_video(video_id="old", published_at=date(2026, 1, 1)),
    ], captured_at=t)
    rows = store.latest_rows(conn, since_days=7, now=date(2026, 5, 30))
    ids = {r["video_id"] for r in rows}
    assert ids == {"new"}
