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

    db_parent = argparse.ArgumentParser(add_help=False)
    db_parent.add_argument("--db", default=DEFAULT_DB)

    parser = argparse.ArgumentParser(prog="short-searcher", parents=[db_parent])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", parents=[db_parent])
    p_search.add_argument("keywords", nargs="+")
    p_search.add_argument("--max", type=int, default=50)

    p_scan = sub.add_parser("scan", parents=[db_parent])
    p_scan.add_argument("channels", nargs="+")
    p_scan.add_argument("--max", type=int, default=50)

    p_report = sub.add_parser("report", parents=[db_parent])
    p_report.add_argument("--sort", default="composite",
                          choices=["velocity", "engagement", "composite", "views"])
    p_report.add_argument("--limit", type=int, default=20)
    p_report.add_argument("--since")
    p_report.add_argument("--export", choices=["csv", "md"])
    p_report.add_argument("--out")

    p_brief = sub.add_parser("brief", parents=[db_parent])
    p_brief.add_argument("--since")
    p_brief.add_argument("--top", type=int, default=10)
    p_brief.add_argument("--format", default="md", choices=["md", "json"])

    args = parser.parse_args(argv)
    conn = store.connect(args.db)

    if args.cmd in ("search", "scan"):
        fetch = search_fn if args.cmd == "search" else scan_fn
        terms = args.keywords if args.cmd == "search" else args.channels
        all_videos = []
        try:
            for term in terms:
                all_videos.extend(fetch(term, max_results=args.max))
        except Exception as exc:  # noqa: BLE001 - surface a clean error, not a traceback
            print(f"error: failed to fetch from source: {exc}", file=sys.stderr)
            return 1
        store.upsert_videos(conn, all_videos)
        print(f"{len(all_videos)} shorts collected, snapshots saved.")
        return 0

    if args.cmd == "report":
        rows = reports.build_report_rows(conn, sort=args.sort,
                                         since_days=_parse_since(args.since),
                                         limit=args.limit)
        render.to_terminal(rows)
        if args.export == "csv":
            path = args.out or "shorts.csv"
            render.to_csv(rows, path)
            print(f"Exported CSV to {path}")
        elif args.export == "md":
            path = args.out or "shorts.md"
            render.to_markdown(rows, path)
            print(f"Exported Markdown to {path}")
        return 0

    if args.cmd == "brief":
        brief = reports.build_brief(conn, since_days=_parse_since(args.since),
                                    top=args.top)
        if args.format == "json":
            print(json.dumps(brief, indent=2))
        else:
            print(render.brief_to_markdown(brief))
        return 0

    return 1  # unreachable: subparsers is required, but a defensive default


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
