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
