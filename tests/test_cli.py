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


def test_scan_collects_into_db(tmp_path, capsys):
    db = tmp_path / "data.db"
    code = cli.main(["scan", "@AltDaily", "--db", str(db)],
                    scan_fn=lambda ch, max_results: [_fake_video(vid="s1")])
    assert code == 0
    assert "saved" in capsys.readouterr().out.lower()
    conn = store.connect(str(db))
    assert len(store.latest_rows(conn)) == 1


def test_report_export_csv_writes_file(tmp_path, capsys):
    db = tmp_path / "data.db"
    out = tmp_path / "out.csv"
    cli.main(["search", "xrp", "--db", str(db)],
             search_fn=lambda kw, max_results: [_fake_video()])
    capsys.readouterr()
    code = cli.main(["report", "--db", str(db), "--export", "csv", "--out", str(out)])
    assert code == 0
    assert out.exists()
    assert "XRP explodes" in out.read_text()
    assert "Exported CSV" in capsys.readouterr().out


def test_search_source_failure_returns_nonzero(tmp_path, capsys):
    db = tmp_path / "data.db"

    def boom(kw, max_results):
        raise RuntimeError("tubescrape down")

    code = cli.main(["search", "xrp", "--db", str(db)], search_fn=boom)
    assert code == 1
    assert "error" in capsys.readouterr().err.lower()


def test_brief_json_shape(tmp_path, capsys):
    db = tmp_path / "data.db"
    cli.main(["search", "xrp", "--db", str(db)],
             search_fn=lambda kw, max_results: [_fake_video()])
    capsys.readouterr()
    code = cli.main(["brief", "--format", "json", "--db", str(db)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["coins"][0]["coin"] == "XRP"
