import json
from datetime import date
from pathlib import Path
import pytest
from short_searcher import sources

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_duration():
    assert sources._parse_duration("42") == 42
    assert sources._parse_duration("1:02") == 62
    assert sources._parse_duration("1:01:00") == 3660


class _FakeResult:
    def __init__(self, title, duration, url):
        self.title = title
        self.duration = duration
        self.view_count = 999       # ignored; enrichment overrides
        self.channel = "AltDaily"
        self.url = url


class _FakeSearchResponse:
    def __init__(self, videos):
        self.videos = videos


class _FakeYouTube:
    def __init__(self, videos):
        self._videos = videos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def search(self, query, max_results=50):
        return _FakeSearchResponse(self._videos)

    def get_channel_videos(self, handle, max_results=50):
        return _FakeSearchResponse(self._videos)


@pytest.fixture
def enrich_from_fixture():
    blob = json.loads((FIXTURES / "ytdlp_video.json").read_text())
    return lambda url: blob


def test_search_keyword_filters_shorts_and_enriches(enrich_from_fixture):
    results = [
        _FakeResult("XRP is about to explode", "42",
                    "https://youtube.com/shorts/abc123"),       # 42s -> Short
        _FakeResult("3 hour BTC livestream", "1:30:00",
                    "https://youtube.com/watch?v=long"),        # too long -> dropped
    ]
    videos = sources.search_keyword(
        "xrp", client_factory=lambda: _FakeYouTube(results),
        enrich=enrich_from_fixture)

    assert len(videos) == 1
    v = videos[0]
    assert v.video_id == "abc123"
    assert v.duration_sec == 42
    assert v.likes == 80
    assert v.comments == 20
    assert v.published_at == date(2026, 5, 20)


def test_scan_channel_uses_channel_endpoint(enrich_from_fixture):
    results = [_FakeResult("XRP is about to explode", "42",
                           "https://youtube.com/shorts/abc123")]
    videos = sources.scan_channel(
        "@AltDaily", client_factory=lambda: _FakeYouTube(results),
        enrich=enrich_from_fixture)
    assert len(videos) == 1
    assert videos[0].channel == "AltDaily"


def test_enrich_failure_skips_one_video():
    results = [_FakeResult("XRP is about to explode", "42",
                           "https://youtube.com/shorts/abc123")]

    def boom(url):
        raise RuntimeError("yt-dlp failed")

    videos = sources.search_keyword(
        "xrp", client_factory=lambda: _FakeYouTube(results), enrich=boom)
    assert videos == []
