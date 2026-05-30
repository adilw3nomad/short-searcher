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
