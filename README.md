# short-searcher

> Find what crypto Shorts people actually want to watch — so we can make more of them.

## The problem

We make crypto YouTube Shorts. Terminal-style videos. Chart backgrounds. Great Wave CRT aesthetic. They perform okay — one got 371 views, 7 likes, 2 subscribers in a day.

But we're guessing what to make next.

We pick coins based on what's pumping. We write scripts based on our own research. We don't know what *other people* are searching for, what hooks are working, or what formats are crushing it.

We need **data** — not gut feel.

## What we researched

We investigated every way to analyze top-performing crypto Shorts on YouTube. Here's what we found.

### The wall

The most valuable metrics for Shorts are **locked inside YouTube Studio**:

| Metric | Why it matters | Can we get it? |
|--------|---------------|----------------|
| Swipe-away rate | The #1 Shorts metric — tells you if your hook works | ❌ Studio only |
| Retention curve | Per-second viewership drop-off | ❌ Studio only |
| Avg view duration | How long people watch | ✅ Analytics API (your channel only) |
| Views | Topline popularity signal | ✅ Public API / scraping |
| Likes / comments / shares | Engagement quality | ✅ Public API / scraping |
| Title & description | What hooks are working | ✅ Public API |

### What's open to us

**tubescrape** — a Python library that talks to YouTube's internal InnerTube API. No API key needed. No OAuth. Can search, get views/likes/comments, channel info, transcripts. Works from Python or CLI.

```python
from tubescrape import YouTube

with YouTube() as yt:
    results = yt.search("crypto altcoins", max_results=50)
    for r in results:
        print(f"{r.title} — {r.views} views")
```

**yt-dlp** — already installed. Can dump full JSON metadata for any video.

```bash
yt-dlp --dump-json --no-download "https://youtube.com/shorts/VIDEO_ID"
```

**What we can't do (and why we're honest about it):**
- Can't see swipe-away rates or retention curves for other channels
- Can't get "trending Shorts by category" — no such API endpoint exists
- Can't get YouTube Studio-level analytics for anyone but ourselves

**What we can do:**
- Search crypto keywords, get top Shorts by view count
- Track view velocity (views/day since publish) to find what's growing fast
- Extract title/description patterns and feed them to an LLM for hook analysis
- Build a daily/weekly report of what's trending

## What we want to create

`short-searcher` should be a **research assistant** for making better Shorts. Not a dashboard — a tool you run, get answers from, then go make a video.

### Phase 1 — Explorer (build this first)

A CLI tool that:

1. **Searches YouTube** for crypto Shorts using keywords we care about
   - `"bitcoin"`, `"ethereum"`, `"crypto"`, `"altcoins"`, `"defi"`, specific coin names
   - Returns title, views, likes, comments, publish date, channel, video URL
2. **Ranks by engagement** — not just views
   - `engagement_rate = (likes + comments) / views`
   - Flags high-engagement shorts even if view count is modest
3. **Dumps to CSV** — so we can analyze in any tool
4. **Spots patterns** — run titles/descriptions through an LLM to identify:
   - Common hook formulas ("THIS is why...", "The ONE coin...")
   - Length sweet spots (30s vs 45s vs 60s)
   - Format patterns (chart bg vs stock footage vs talking head)
   - Top performing channels

**Example output:**
```
Top crypto Shorts this week — sorted by engagement rate:
┌──────────────────────────────────────┬──────────┬──────┬──────┬───────┐
│ Title                                │ Views    │ Rate │ Len  │ Chan  │
├──────────────────────────────────────┼──────────┼──────┼──────┼───────┤
│ This coin just did WHAT??!           │ 142,503  │ 8.2% │ 32s  │ @C... │
│ 3 reasons XRP is about to explode    │ 89,220   │ 5.1% │ 45s  │ @A... │
│ ...                                  │          │      │      │       │
└──────────────────────────────────────┴──────────┴──────┴──────┴───────┘

📊 Trending hooks this week:
  "THIS is why [COIN] is [prediction]" — 3 shorts in top 20
  "The ONE coin nobody is talking about" — 2 shorts in top 20
```

### Phase 2 — Watcher (optional future)

Run on a cron job. Track the same keywords daily. Alert on:

- Shorts that gained 10K+ views in 24h
- New channels breaking out with crypto content
- Shifts in what's trending (e.g., "gasless stablecoins" suddenly spiking)

### Non-goals (for now)

- A fancy web dashboard — CLI output is fine
- Predicting what will go viral — just showing what already is
- Automating video creation — this is research, not production

## Your idea

The structure is loose on purpose. You might have a better approach.

Some open questions:

- **Keywords vs channels**: Should we search by keyword, or scan specific channels (CoinBureau, Altcoin Daily, etc.) and see what's working for them?
- **Frequency**: Daily scan? Weekly report? On-demand only?
- **LLM analysis**: Use Claude/GPT to analyze hook patterns, or keep it purely quantitative?
- **Output format**: CSV dump for spreadsheets? Markdown report? Telegram message?
- **Metrics mix**: Should we weight by views, engagement rate, growth velocity, or some composite score?

The key insight is: we're making Shorts, and we want to make ones people actually watch. `short-searcher` should point us in the right direction — whatever that looks like.

## Contributing

This is a living README. If you have ideas, edit this file and build the tool. The repo is brand new — make it yours.

## License

MIT
