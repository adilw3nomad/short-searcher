# short-searcher — Phase 1 (Explorer) Design

**Date:** 2026-05-30
**Status:** Approved (design), pending implementation plan

## Purpose

short-searcher is a CLI research assistant that finds which crypto YouTube Shorts
people actually watch, so we can make more of them. Its primary consumer is
**Mercury** — the LLM agent that operates the HADES pipeline (`~/projects/hades`)
to produce Shorts daily. Today Mercury picks coins "based on what's pumping / own
research." short-searcher replaces that guesswork with data: it collects and
structures real Shorts performance, and Mercury interprets it to choose what to
make next.

Phase 1 is on-demand collection + reporting. It is **quantitative only** — no
LLM call inside short-searcher, because the downstream consumer (Mercury) is
already an LLM and does the pattern interpretation. Phase 2 (Watcher, cron
alerts) and an optional internal LLM step are explicitly deferred.

## Tech choices

- **Python** — both data sources (`tubescrape`, `yt-dlp`) are Python/CLI.
- **Two-tier collection.** tubescrape `search()` / `get_channel_videos()` only
  return `title, duration, view_count, published_text (relative), channel, url`
  — **no likes, comments, or exact publish date.** So discovery is cheap via
  tubescrape, then each kept Short is **enriched** with
  `yt-dlp --dump-json <url>` for `like_count`, `comment_count`, exact
  `upload_date`, and precise `duration`. We filter to Shorts (`duration <= 60s`)
  *before* enriching so we never spend a yt-dlp call on a long video.
- **SQLite** as the source of truth — required to "track over time" (velocity,
  growth). Repeated runs snapshot metrics; reports derive from snapshots.
- **Rich** for the terminal table; CSV + Markdown exporters render from the DB.
- **pytest** for tests.

## What we can and cannot get (from research)

- ✅ Search crypto keywords, top Shorts by views; views/likes/comments;
  title/description; publish date; channel; duration.
- ❌ Swipe-away rate, retention curves, Studio analytics for other channels;
  "trending Shorts by category" (no such API).
- View velocity (views/day) is our growth proxy, computed from snapshots.

## Data model (SQLite)

Two tables. Metrics are **derived at report time**, never stored denormalized.

**`videos`** — identity + slow-changing facts, one row per video:

```
video_id      TEXT PRIMARY KEY   -- YouTube ID
title         TEXT
channel       TEXT
channel_id    TEXT
duration_sec  INTEGER
published_at  TEXT               -- ISO date
url           TEXT
first_seen_at TEXT               -- when we first discovered it
```

**`snapshots`** — one row per (video, observation time); this makes velocity real:

```
id          INTEGER PRIMARY KEY
video_id    TEXT  -> videos.video_id
captured_at TEXT               -- ISO timestamp of the run
views       INTEGER
likes       INTEGER
comments    INTEGER
```

- Engagement rate = `(likes + comments) / views` from the latest snapshot.
- Lifetime velocity = `views / age_days` (age from `published_at`).
- Recent velocity = `Δviews / Δhours` between a video's two most-recent snapshots.
- A `search_runs` table is intentionally omitted (YAGNI) — `first_seen_at` +
  snapshots already capture discovery history.

## Components (package `short_searcher/`)

Each module has one job and a clean interface; pure logic is isolated from I/O.

- **`models.py`** — one dataclass `Video` (the common shape both sources emit):
  `video_id, title, channel, channel_id, duration_sec, published_at, url,
  views, likes, comments`.

- **`sources.py`** — discovery + enrichment; the **only** module touching
  tubescrape/yt-dlp.
  - `search_keyword(keyword: str, max_results: int = 50) -> list[Video]`
  - `scan_channel(channel: str, max_results: int = 50) -> list[Video]`
  - Internal helpers: `_parse_duration(text) -> int` (tubescrape `"1:02"` →
    seconds), `_enrich(url) -> dict` (runs `yt-dlp --dump-json`, returns
    `like_count, comment_count, upload_date, duration, view_count`).
  - Flow per query: tubescrape discover → keep `duration_sec <= 60` → `_enrich`
    each kept item → build `Video`. Channel input accepts `@handle` or URL.
    Isolating both libraries here means a break or swap touches only this file.

- **`store.py`** — SQLite; owns schema + all SQL.
  - `connect(db_path) -> Connection` (creates schema `IF NOT EXISTS`)
  - `upsert_videos(conn, videos)` — upserts `videos`, appends a `snapshots` row
    stamped now
  - `latest_snapshots(conn, filters) -> list[Row]`
  - `velocity_rows(conn) -> list[Row]` — joins the two most-recent snapshots per
    video

- **`metrics.py`** — pure functions, zero I/O (most-tested module):
  `engagement_rate(v)`, `lifetime_velocity(v)`, `recent_velocity(curr, prev)`,
  `composite(...)`. All guard divide-by-zero → `0.0`.

- **`coins.py`** — ticker→name dictionary (BTC→Bitcoin, XRP→Ripple,
  LUNC→Terra Luna Classic, …) + `extract_coins(title, description) -> list[str]`.
  Turns "videos" into "which coins/topics are winning" — the question Mercury asks.

- **`render.py`** — `to_terminal(rows)` (Rich), `to_csv(rows, path)`,
  `to_markdown(rows, path)`. All consume the same row dicts.

- **`cli.py`** — argparse wiring for the subcommands.

## CLI surface

Default DB `~/.short-searcher/data.db`, overridable with `--db`.

```
short-searcher search "bitcoin" "altcoins" [--max 50]
short-searcher scan @CoinBureau @AltcoinDaily [--max 50]
short-searcher report [--sort velocity|engagement|composite|views]
                      [--limit 20] [--since 7d] [--export csv|md] [--out PATH]
short-searcher brief  [--since 7d] [--top 10] [--format md|json]
```

### Data flow

- **`search` / `scan`** (collect): parse args → `sources.*` fetch `Video`s →
  `store.upsert_videos` (updates `videos`, appends a `snapshots` row) → print a
  short summary (`"42 videos, 12 new, snapshots saved"`). Running these over days
  builds the time series.
- **`report`** (read-only): `store` pulls latest (+ previous) snapshots →
  `metrics` computes all three scores → sort by `--sort` (default `composite`) →
  `render` prints the Rich table, and exports CSV/MD if `--export` given. Never
  hits the network.
- **`brief`** (read-only, Mercury handoff): aggregates snapshots **per coin**
  (via `coins.extract_coins`) and emits, for each trending coin in the window:
  aggregate signal (total/median views, engagement, recent velocity), the
  **top-performing Shorts verbatim** (title + stats, so Mercury reads real
  hooks), and the count of Shorts in the window (saturation signal).
  `--format json` is the machine handoff; `md` is human-readable.

## Mercury integration

short-searcher stays **decoupled** from HADES — it never imports or writes HADES
files, matching the ecosystem contract (tools report; agents tune their own
config/YAML). The only contract is the brief's JSON shape, documented in the
README.

Mercury's loop becomes:

1. `short-searcher brief --format json`
2. Pick a coin + angle informed by what is actually performing (and what is
   saturated).
3. Write `coins/<coin>.yaml` in HADES (hook, tagline, script, title, …).
4. Run the HADES CLI to render + (optionally) upload.

The brief's per-coin verbatim top Shorts let Mercury infer hook/title/length
patterns itself — no internal LLM call in short-searcher needed.

## Error handling

Proportional to a personal research tool.

- **Scraping failures** (tubescrape down, rate-limited, video unavailable):
  `sources` catches per-item, logs a warning, skips that item. A whole-search
  failure exits non-zero with a clear message.
- **Enrichment failures** (`yt-dlp` errors on one video, comments disabled →
  null `comment_count`): treat missing counts as `0`, skip a video only if
  `yt-dlp` fails entirely for it; the rest of the run continues.
- **Transient network**: one retry with short backoff in `sources`; no retry
  framework.
- **Missing/zero data**: metrics guard divide-by-zero → `0.0`; the row still
  shows, flagged `—` in the table.
- **DB**: schema created on first connect; no migration system in Phase 1.

## Testing (pytest)

- **`metrics.py`** — fully unit-tested with hand-picked numbers, including
  zero-view, brand-new, and no-prior-snapshot edge cases. Pure functions, no mocks.
- **`store.py`** — against in-memory SQLite (`:memory:`): upsert dedups, second
  snapshot appends, velocity join picks the correct two rows.
- **`coins.py`** — `extract_coins` tags known tickers/names, ignores noise.
- **`render.py`** — CSV/Markdown asserted against expected strings; terminal
  table smoke-tested.
- **`sources.py`** — `_parse_duration` unit-tested directly. Discovery/enrichment
  tested against **saved fixture payloads** (a captured tubescrape result list +
  a captured `yt-dlp --dump-json` blob) with the tubescrape client and the
  `yt-dlp` subprocess call mocked — deterministic and offline.
- **`cli.py`** — one integration test per subcommand: fixtures → temp DB →
  assert output (including `brief --format json` shape).

## Non-goals (Phase 1)

- Phase 2 Watcher / cron alerts (designed to slot in as a `watch` subcommand
  reusing the same snapshot data — no new plumbing).
- Internal LLM analysis inside short-searcher (Mercury is the LLM).
- Web dashboard; virality prediction; automating video creation.
