# Shared fixtures are added in later tasks.
from datetime import date
import pytest
from short_searcher.models import Video


@pytest.fixture
def sample_video():
    def _make(video_id="abc123", views=1000, likes=80, comments=20,
              title="XRP is about to explode", channel="AltDaily",
              duration_sec=42, published_at=date(2026, 5, 20)):
        return Video(
            video_id=video_id, title=title, channel=channel, channel_id="UC1",
            duration_sec=duration_sec, published_at=published_at,
            url=f"https://youtube.com/shorts/{video_id}",
            views=views, likes=likes, comments=comments,
        )
    return _make
