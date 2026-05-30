from datetime import date
from short_searcher.models import Video


def test_video_holds_fields():
    v = Video(
        video_id="abc123", title="XRP to the moon", channel="AltDaily",
        channel_id="UC1", duration_sec=42, published_at=date(2026, 5, 20),
        url="https://youtube.com/shorts/abc123", views=1000, likes=80, comments=20,
    )
    assert v.video_id == "abc123"
    assert v.duration_sec == 42
    assert v.published_at == date(2026, 5, 20)
    assert v.likes + v.comments == 100
