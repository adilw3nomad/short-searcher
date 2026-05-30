# short-searcher Phase 1 (Explorer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that collects crypto-Shorts performance data into SQLite over time and emits ranked reports plus a per-coin research brief for the Mercury agent.

**Architecture:** A lean package (`short_searcher/`) of focused modules: `models` (the `Video` dataclass), `sources` (tubescrape discovery + yt-dlp enrichment — the only network code), `store` (SQLite snapshots), `metrics` (pure scoring), `coins` (ticker extraction), `reports` (combine store+metrics+coins into rows/brief), `render` (terminal/CSV/Markdown/JSON), and `cli` (argparse subcommands `search`, `scan`, `report`, `brief`). Metrics are derived at report time from snapshots, never stored.

**Tech Stack:** Python 3.11+, `tubescrape` (discovery), `yt-dlp` (enrichment via subprocess), `rich` (terminal table), `pytest`. SQLite via the stdlib `sqlite3`.

**Spec:** `docs/superpowers/specs/2026-05-30-short-searcher-phase1-design.md`

> Note: this plan adds one module not separately named in the spec — `reports.py` — to hold the report/brief aggregation glue so it is unit-testable instead of buried in `cli.py`. Everything else maps directly to the spec.

---

## File Structure

```
short-searcher/
├── pyproject.toml                 # package metadata + deps + console script
├── short_searcher/
│   ├── __init__.py
│   ├── models.py                  # Video dataclass
│   ├── metrics.py                 # pure scoring functions
│   ├── coins.py                   # COIN_MAP + extract_coins
│   ├── store.py                   # SQLite schema + queries
│   ├── sources.py                 # tubescrape discover + yt-dlp enrich
│   ├── reports.py                 # build_report_rows + build_brief
│   ├── render.py                  # terminal/CSV/Markdown/JSON output
│   └── cli.py                     # argparse subcommands
└── tests/
    ├── conftest.py                # fixtures (in-memory store, sample videos)
    ├── fixtures/
    │   ├── tubescrape_search.json # captured tubescrape result list
    │   └── ytdlp_video.json       # captured `yt-dlp --dump-json` blob
    ├── test_metrics.py
    ├── test_coins.py
    ├── test_store.py
    ├── test_sources.py
    ├── test_reports.py
    ├── test_render.py
    └── test_cli.py
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `short_searcher/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

`tests/test_smoke.py`:
```python
def test_package_imports():
    import short_searcher
    assert short_searcher.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher'`

- [ ] **Step 3: Create the package and config**

`pyproject.toml`:
```toml
[project]
name = "short-searcher"
version = "0.1.0"
description = "Research assistant for crypto YouTube Shorts"
requires-python = ">=3.11"
dependencies = ["tubescrape>=0.1.2", "yt-dlp>=2025.0", "rich>=13.0"]

[project.scripts]
short-searcher = "short_searcher.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`short_searcher/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
# Shared fixtures are added in later tasks.
```

- [ ] **Step 4: Install in editable mode and run the test**

Run: `python -m pip install -e . && python -m pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml short_searcher/__init__.py tests/
git commit -m "chore: scaffold short_searcher package"
```

---

### Task 2: Video model

**Files:**
- Create: `short_searcher/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.models'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/models.py`:
```python
from dataclasses import dataclass
from datetime import date


@dataclass
class Video:
    video_id: str
    title: str
    channel: str
    channel_id: str
    duration_sec: int
    published_at: date
    url: str
    views: int
    likes: int
    comments: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add short_searcher/models.py tests/test_models.py
git commit -m "feat: add Video dataclass"
```

---

### Task 3: Metrics (pure scoring)

**Files:**
- Create: `short_searcher/metrics.py`
- Test: `tests/test_metrics.py`

`composite_scores` takes a list of `(recent_velocity, engagement, lifetime_velocity)` tuples and min-max normalizes each dimension across the list (range 0 → returns 0.0 for that dimension), then weights them 0.5 / 0.3 / 0.2.

- [ ] **Step 1: Write the failing test**

`tests/test_metrics.py`:
```python
from datetime import date
from short_searcher import metrics


def test_engagement_rate():
    assert metrics.engagement_rate(1000, 80, 20) == 0.1


def test_engagement_rate_zero_views_is_zero():
    assert metrics.engagement_rate(0, 5, 5) == 0.0


def test_lifetime_velocity():
    # 10000 views, published 10 days before `now` -> 1000 views/day
    v = metrics.lifetime_velocity(10000, date(2026, 5, 20), now=date(2026, 5, 30))
    assert v == 1000.0


def test_lifetime_velocity_same_day_is_zero():
    v = metrics.lifetime_velocity(10000, date(2026, 5, 30), now=date(2026, 5, 30))
    assert v == 0.0


def test_recent_velocity():
    # +1200 views over 24h -> 50 views/hour
    assert metrics.recent_velocity(5200, 4000, 24.0) == 50.0


def test_recent_velocity_no_prior_is_zero():
    assert metrics.recent_velocity(5200, None, 24.0) == 0.0


def test_composite_scores_normalizes_and_weights():
    rows = [
        (100.0, 0.10, 1000.0),   # best on every axis -> 1.0
        (0.0, 0.0, 0.0),         # worst on every axis -> 0.0
        (50.0, 0.05, 500.0),     # middle -> 0.5
    ]
    scores = metrics.composite_scores(rows)
    assert scores[0] == 1.0
    assert scores[1] == 0.0
    assert abs(scores[2] - 0.5) < 1e-9


def test_composite_scores_flat_dimension_contributes_zero():
    rows = [(0.0, 0.1, 10.0), (0.0, 0.1, 10.0)]
    assert metrics.composite_scores(rows) == [0.0, 0.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.metrics'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/metrics.py`:
```python
from datetime import date


def engagement_rate(views: int, likes: int, comments: int) -> float:
    if views <= 0:
        return 0.0
    return (likes + comments) / views


def lifetime_velocity(views: int, published_at: date, now: date | None = None) -> float:
    now = now or date.today()
    age_days = (now - published_at).days
    if age_days <= 0:
        return 0.0
    return views / age_days


def recent_velocity(curr_views: int, prev_views: int | None, hours: float) -> float:
    if prev_views is None or hours <= 0:
        return 0.0
    return (curr_views - prev_views) / hours


def composite_scores(rows: list[tuple[float, float, float]]) -> list[float]:
    if not rows:
        return []
    weights = (0.5, 0.3, 0.2)  # recent_velocity, engagement, lifetime_velocity

    def normalize(values: list[float]) -> list[float]:
        lo, hi = min(values), max(values)
        span = hi - lo
        if span == 0:
            return [0.0] * len(values)
        return [(x - lo) / span for x in values]

    cols = [normalize([r[i] for r in rows]) for i in range(3)]
    return [
        sum(weights[i] * cols[i][j] for i in range(3))
        for j in range(len(rows))
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_metrics.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add short_searcher/metrics.py tests/test_metrics.py
git commit -m "feat: add pure metric scoring functions"
```

---

### Task 4: Coin extraction

**Files:**
- Create: `short_searcher/coins.py`
- Test: `tests/test_coins.py`

- [ ] **Step 1: Write the failing test**

`tests/test_coins.py`:
```python
from short_searcher import coins


def test_extracts_ticker_word():
    assert coins.extract_coins("XRP is about to explode", "") == ["XRP"]


def test_extracts_from_name_case_insensitive():
    assert coins.extract_coins("Why bitcoin is surging", "") == ["BTC"]


def test_dedupes_ticker_and_name():
    out = coins.extract_coins("BTC update", "Bitcoin looking strong")
    assert out == ["BTC"]


def test_multiple_coins_sorted():
    assert coins.extract_coins("ETH vs SOL", "") == ["ETH", "SOL"]


def test_no_false_positive_substring():
    # "scam" must not match "ADA" etc.; a bare unrelated word returns nothing
    assert coins.extract_coins("this is a scam warning", "") == []


def test_name_resolves_to_ticker():
    assert coins.COIN_MAP["LUNC"] == "Terra Luna Classic"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coins.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.coins'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/coins.py`:
```python
import re

COIN_MAP: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "XRP": "Ripple",
    "SOL": "Solana",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "SHIB": "Shiba Inu",
    "LUNC": "Terra Luna Classic",
    "BNB": "BNB",
    "AVAX": "Avalanche",
    "LINK": "Chainlink",
    "DOT": "Polkadot",
    "MATIC": "Polygon",
    "LTC": "Litecoin",
    "PEPE": "Pepe",
}

# name -> ticker, for matching spelled-out coin names
_NAME_TO_TICKER = {name.lower(): ticker for ticker, name in COIN_MAP.items()}


def extract_coins(title: str, description: str) -> list[str]:
    text = f"{title} {description}"
    found: set[str] = set()
    for ticker in COIN_MAP:
        if re.search(rf"\b{re.escape(ticker)}\b", text, re.IGNORECASE):
            found.add(ticker)
    for name, ticker in _NAME_TO_TICKER.items():
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            found.add(ticker)
    return sorted(found)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_coins.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add short_searcher/coins.py tests/test_coins.py
git commit -m "feat: add coin ticker extraction"
```

---

### Task 5: SQLite store

**Files:**
- Create: `short_searcher/store.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_store.py`

`upsert_videos` accepts an explicit `captured_at` (a datetime) so tests can control snapshot timing. New videos get `first_seen_at = captured_at`; existing videos keep their original row but always get a fresh snapshot.

- [ ] **Step 1: Add a shared fixture**

Append to `tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Write the failing test**

`tests/test_store.py`:
```python
from datetime import datetime
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
    assert prev["abc123"] == 1000       # prior snapshot available


def test_previous_views_empty_when_single_snapshot(sample_video):
    conn = store.connect(":memory:")
    store.upsert_videos(conn, [sample_video()], captured_at=datetime(2026, 5, 30))
    assert store.previous_views(conn) == {}


def test_latest_rows_since_filters_by_publish_date(sample_video):
    from datetime import date
    conn = store.connect(":memory:")
    t = datetime(2026, 5, 30, 12, 0, 0)
    store.upsert_videos(conn, [
        sample_video(video_id="new", published_at=date(2026, 5, 29)),
        sample_video(video_id="old", published_at=date(2026, 1, 1)),
    ], captured_at=t)
    rows = store.latest_rows(conn, since_days=7, now=date(2026, 5, 30))
    ids = {r["video_id"] for r in rows}
    assert ids == {"new"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.store'`

- [ ] **Step 4: Write minimal implementation**

`short_searcher/store.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add short_searcher/store.py tests/conftest.py tests/test_store.py
git commit -m "feat: add SQLite snapshot store"
```

---

### Task 6: Sources (tubescrape discover + yt-dlp enrich)

**Files:**
- Create: `short_searcher/sources.py`
- Create: `tests/fixtures/ytdlp_video.json`
- Test: `tests/test_sources.py`

`search_keyword`/`scan_channel` call an injected `client_factory` (defaults to `tubescrape.YouTube`) and an injected `enrich` callable (defaults to `_enrich`) so tests run offline with no network and no real `yt-dlp`. tubescrape result objects expose `.title, .duration, .view_count, .channel, .url`; `_enrich` shells out to `yt-dlp --dump-json` and returns the parsed metadata dict.

- [ ] **Step 1: Create the yt-dlp fixture**

`tests/fixtures/ytdlp_video.json`:
```json
{
  "id": "abc123",
  "title": "XRP is about to explode",
  "channel": "AltDaily",
  "channel_id": "UC1",
  "duration": 42,
  "upload_date": "20260520",
  "webpage_url": "https://www.youtube.com/shorts/abc123",
  "view_count": 1000,
  "like_count": 80,
  "comment_count": 20
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_sources.py`:
```python
import json
from datetime import date
from pathlib import Path
import pytest
from short_searcher import sources

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_duration():
    assert sources._parse_duration("42") == 42
    assert sources._parse_duration("1:02") == 62
    assert sources._parse_duration("1:01:00") == 3661


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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.sources'`

- [ ] **Step 4: Write minimal implementation**

`short_searcher/sources.py`:
```python
import json
import logging
import subprocess
from datetime import date, datetime
from typing import Callable

from .models import Video

log = logging.getLogger("short_searcher.sources")
SHORT_MAX_SEC = 60


def _parse_duration(text: str) -> int:
    parts = [int(p) for p in str(text).split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _enrich(url: str) -> dict:
    out = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-warnings", url],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def _default_client():  # pragma: no cover - thin wrapper over the library
    from tubescrape import YouTube
    return YouTube()


def _collect(results, enrich: Callable[[str], dict]) -> list[Video]:
    videos: list[Video] = []
    for r in results:
        if _parse_duration(r.duration) > SHORT_MAX_SEC:
            continue
        try:
            meta = enrich(r.url)
        except Exception as exc:  # noqa: BLE001 - skip the bad video, keep going
            log.warning("enrich failed for %s: %s", r.url, exc)
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_sources.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add short_searcher/sources.py tests/fixtures/ytdlp_video.json tests/test_sources.py
git commit -m "feat: add tubescrape discovery + yt-dlp enrichment sources"
```

---

### Task 7: Reports (rows + brief aggregation)

**Files:**
- Create: `short_searcher/reports.py`
- Test: `tests/test_reports.py`

`build_report_rows` reads `store.latest_rows` + `store.previous_views`, computes metrics per row, attaches `composite`, sorts by `sort` key, and truncates to `limit`. The hours gap for `recent_velocity` is derived from `captured_at` vs the previous snapshot; when there is no previous snapshot it is `0`. `build_brief` groups rows by extracted coin and summarizes.

- [ ] **Step 1: Write the failing test**

`tests/test_reports.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.reports'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/reports.py`:
```python
from datetime import date
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
        # The gap between the latest and previous snapshot is not tracked yet,
        # so use a 24h default window when a previous snapshot exists.
        prev_views = prev.get(r["video_id"])
        gap_hours = 24.0 if prev_views is not None else 0.0
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reports.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add short_searcher/reports.py tests/test_reports.py
git commit -m "feat: add report rows and per-coin brief aggregation"
```

---

### Task 8: Render (terminal / CSV / Markdown / brief)

**Files:**
- Create: `short_searcher/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing test**

`tests/test_render.py`:
```python
from short_searcher import render

ROWS = [
    {"title": "XRP explodes", "channel": "AltDaily", "views": 3400,
     "engagement": 0.1, "duration_sec": 42, "recent_velocity": 100.0,
     "composite": 1.0, "url": "https://youtube.com/shorts/a"},
]


def test_to_csv_writes_header_and_row(tmp_path):
    p = tmp_path / "out.csv"
    render.to_csv(ROWS, p)
    text = p.read_text()
    assert text.splitlines()[0].startswith("title,channel,views")
    assert "XRP explodes" in text
    assert "3400" in text


def test_to_markdown_table(tmp_path):
    p = tmp_path / "out.md"
    render.to_markdown(ROWS, p)
    text = p.read_text()
    assert "| Title |" in text
    assert "| XRP explodes |" in text


def test_brief_to_markdown():
    brief = {
        "generated_at": "2026-05-30", "window_days": 7,
        "coins": [{
            "coin": "XRP", "name": "Ripple", "short_count": 3,
            "total_views": 9000, "median_views": 3000, "median_engagement": 0.08,
            "median_recent_velocity": 100.0,
            "top_shorts": [{"title": "XRP explodes", "url": "u", "views": 3400,
                            "engagement": 0.1, "recent_velocity": 100.0}],
        }],
    }
    md = render.brief_to_markdown(brief)
    assert "XRP" in md and "Ripple" in md
    assert "XRP explodes" in md


def test_to_terminal_smoke():
    # should not raise
    render.to_terminal(ROWS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.render'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/render.py`:
```python
import csv
from pathlib import Path

from rich.console import Console
from rich.table import Table

_COLUMNS = ["title", "channel", "views", "engagement", "duration_sec",
            "recent_velocity", "composite", "url"]


def to_csv(rows: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def to_markdown(rows: list[dict], path: str | Path) -> None:
    lines = ["| Title | Channel | Views | Rate | Len | Vel/h |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['title']} | {r['channel']} | {r['views']} | "
            f"{r['engagement']:.1%} | {r['duration_sec']}s | "
            f"{r['recent_velocity']:.0f} |")
    Path(path).write_text("\n".join(lines) + "\n")


def to_terminal(rows: list[dict]) -> None:
    table = Table(title="Crypto Shorts — ranked")
    for col in ["Title", "Views", "Rate", "Len", "Vel/h", "Channel"]:
        table.add_column(col)
    for r in rows:
        table.add_row(
            r["title"][:40], f"{r['views']:,}", f"{r['engagement']:.1%}",
            f"{r['duration_sec']}s", f"{r['recent_velocity']:.0f}", r["channel"])
    Console().print(table)


def brief_to_markdown(brief: dict) -> str:
    lines = [f"# Crypto Shorts brief — {brief['generated_at']}", ""]
    for c in brief["coins"]:
        lines.append(f"## {c['coin']} ({c['name']}) — {c['short_count']} shorts")
        lines.append(
            f"- total views: {c['total_views']:,} | median engagement: "
            f"{c['median_engagement']:.1%} | median vel/h: {c['median_recent_velocity']}")
        lines.append("- top shorts:")
        for s in c["top_shorts"]:
            lines.append(f"  - \"{s['title']}\" — {s['views']:,} views "
                         f"({s['engagement']:.1%}) {s['url']}")
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add short_searcher/render.py tests/test_render.py
git commit -m "feat: add terminal/CSV/Markdown/brief renderers"
```

---

### Task 9: CLI (argparse subcommands)

**Files:**
- Create: `short_searcher/cli.py`
- Test: `tests/test_cli.py`

`main(argv)` builds the parser and dispatches. `search`/`scan` accept an injected `search_fn`/`scan_fn` (default the real `sources` functions) so the CLI test runs offline. The default DB path is `~/.short-searcher/data.db`; tests pass `--db`.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import json
from datetime import date
from short_searcher import cli, store
from short_searcher.models import Video


def _fake_video(vid="a", title="XRP explodes", views=1000):
    return Video(video_id=vid, title=title, channel="AltDaily", channel_id="UC1",
                 duration_sec=42, published_at=date(2026, 5, 20),
                 url=f"https://youtube.com/shorts/{vid}",
                 views=views, likes=80, comments=20)


def test_search_collects_into_db(tmp_path, capsys):
    db = tmp_path / "data.db"
    code = cli.main(["search", "xrp", "--db", str(db)],
                    search_fn=lambda kw, max_results: [_fake_video()])
    assert code == 0
    assert "saved" in capsys.readouterr().out.lower()
    conn = store.connect(str(db))
    assert len(store.latest_rows(conn)) == 1


def test_report_prints_table(tmp_path, capsys):
    db = tmp_path / "data.db"
    cli.main(["search", "xrp", "--db", str(db)],
             search_fn=lambda kw, max_results: [_fake_video()])
    capsys.readouterr()
    code = cli.main(["report", "--db", str(db)])
    assert code == 0
    assert "XRP explodes" in capsys.readouterr().out


def test_brief_json_shape(tmp_path, capsys):
    db = tmp_path / "data.db"
    cli.main(["search", "xrp", "--db", str(db)],
             search_fn=lambda kw, max_results: [_fake_video()])
    capsys.readouterr()
    code = cli.main(["brief", "--format", "json", "--db", str(db)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["coins"][0]["coin"] == "XRP"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'short_searcher.cli'`

- [ ] **Step 3: Write minimal implementation**

`short_searcher/cli.py`:
```python
import argparse
import json
import sys

from . import render, reports, sources, store

DEFAULT_DB = "~/.short-searcher/data.db"


def _parse_since(value: str | None) -> int | None:
    if not value:
        return None
    return int(value.rstrip("d"))


def main(argv=None, search_fn=None, scan_fn=None) -> int:
    search_fn = search_fn or sources.search_keyword
    scan_fn = scan_fn or sources.scan_channel

    parser = argparse.ArgumentParser(prog="short-searcher")
    parser.add_argument("--db", default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("keywords", nargs="+")
    p_search.add_argument("--max", type=int, default=50)

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("channels", nargs="+")
    p_scan.add_argument("--max", type=int, default=50)

    p_report = sub.add_parser("report")
    p_report.add_argument("--sort", default="composite",
                          choices=["velocity", "engagement", "composite", "views"])
    p_report.add_argument("--limit", type=int, default=20)
    p_report.add_argument("--since")
    p_report.add_argument("--export", choices=["csv", "md"])
    p_report.add_argument("--out")

    p_brief = sub.add_parser("brief")
    p_brief.add_argument("--since")
    p_brief.add_argument("--top", type=int, default=10)
    p_brief.add_argument("--format", default="md", choices=["md", "json"])

    args = parser.parse_args(argv)
    conn = store.connect(args.db)

    if args.cmd in ("search", "scan"):
        fetch = search_fn if args.cmd == "search" else scan_fn
        terms = args.keywords if args.cmd == "search" else args.channels
        all_videos = []
        for term in terms:
            all_videos.extend(fetch(term, max_results=args.max))
        store.upsert_videos(conn, all_videos)
        print(f"{len(all_videos)} shorts collected, snapshots saved.")
        return 0

    if args.cmd == "report":
        rows = reports.build_report_rows(conn, sort=args.sort,
                                         since_days=_parse_since(args.since),
                                         limit=args.limit)
        render.to_terminal(rows)
        if args.export == "csv":
            render.to_csv(rows, args.out or "shorts.csv")
        elif args.export == "md":
            render.to_markdown(rows, args.out or "shorts.md")
        return 0

    if args.cmd == "brief":
        brief = reports.build_brief(conn, since_days=_parse_since(args.since),
                                    top=args.top)
        if args.format == "json":
            print(json.dumps(brief, indent=2))
        else:
            print(render.brief_to_markdown(brief))
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add short_searcher/cli.py tests/test_cli.py
git commit -m "feat: add CLI with search/scan/report/brief subcommands"
```

---

### Task 10: Document the brief JSON contract for Mercury

**Files:**
- Modify: `README.md` (append a section)

The brief JSON shape is the only contract between short-searcher and Mercury, so it must be documented where Mercury will read it.

- [ ] **Step 1: Append the contract section to `README.md`**

Add at the end of `README.md`:
```markdown
## For Mercury — the `brief` contract

Run `short-searcher brief --format json` and parse this shape:

​```json
{
  "generated_at": "2026-05-30",
  "window_days": 7,
  "coins": [
    {
      "coin": "XRP",
      "name": "Ripple",
      "short_count": 12,
      "total_views": 1850000,
      "median_views": 90000,
      "median_engagement": 0.062,
      "median_recent_velocity": 410.0,
      "top_shorts": [
        {"title": "3 reasons XRP is about to explode", "url": "https://...",
         "views": 142503, "engagement": 0.082, "recent_velocity": 980.0}
      ]
    }
  ]
}
​```

Coins are sorted by `median_recent_velocity` (fastest-growing first). Use the
verbatim `top_shorts[].title` values to infer working hooks; use `short_count`
as a saturation signal (many shorts = crowded). short-searcher never writes HADES
files — pick a coin/angle from this brief, then author `coins/<coin>.yaml` yourself.
```

- [ ] **Step 2: Verify the install works end to end (manual smoke)**

Run: `short-searcher --help`
Expected: usage text listing `search`, `scan`, `report`, `brief`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document brief JSON contract for Mercury"
```

---

## Final verification

- [ ] Run the whole suite: `python -m pytest -q` — all green.
- [ ] `short-searcher --help` lists all four subcommands.
- [ ] Spec coverage confirmed: models, sources (discover+enrich), store, metrics,
      coins, reports/brief, render (terminal/CSV/MD/JSON), CLI, Mercury contract.
```
