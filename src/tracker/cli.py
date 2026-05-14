from __future__ import annotations

import argparse
import json
import sys

from datetime import date

from .analyze import detect_signals
from .notify import post as post_signals
from .render import render as render_site
from .scrapers import apple_refurb, iosys
from .storage import load_history, save_snapshot
from . import news as news_mod
from . import watch as watch_mod


SCRAPERS = {
    "apple_refurb": apple_refurb.fetch,
    "iosys": iosys.fetch,
}


def cmd_fetch(args: argparse.Namespace) -> int:
    sources = args.sources or list(SCRAPERS.keys())
    all_listings = []
    errors = []
    for name in sources:
        fn = SCRAPERS.get(name)
        if fn is None:
            print(f"unknown source: {name}", file=sys.stderr)
            continue
        try:
            items = fn()
            print(f"[{name}] {len(items)} listings")
            all_listings.extend(items)
        except Exception as e:
            errors.append((name, repr(e)))
            print(f"[{name}] ERROR: {e!r}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps([l.to_dict() for l in all_listings], ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    path = save_snapshot(all_listings)
    print(f"snapshot saved: {path}")
    return 0 if not errors else 1


def cmd_notify(args: argparse.Namespace) -> int:
    from .analyze import BuySignal
    from .storage import LATEST_FILE

    if args.test:
        signals = [
            BuySignal(
                kind="new_window_low",
                source="iosys",
                memory_gb=24,
                title="[TEST] Mac mini M4 (24GB / 512GB SSD) — webhook疎通確認",
                price_jpy=119800,
                url="https://example.com/test",
                prev_low_jpy=124800,
                window_days=30,
            )
        ]
        print("posting test signal...")
        post_signals(signals)
        return 0

    if not LATEST_FILE.exists():
        print("no snapshot yet; run `tracker fetch` first", file=sys.stderr)
        return 1
    latest = json.loads(LATEST_FILE.read_text())
    signals = detect_signals(latest.get("listings", []), load_history())
    print(f"detected {len(signals)} signal(s)")
    post_signals(signals)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    path = render_site()
    print(f"site rendered: {path}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Sub-daily Apple-refurb watcher: alert only on previously-unseen SKUs."""
    signals, changed = watch_mod.run(today=date.today().isoformat())
    print(f"new SKUs: {len(signals)} | state_changed: {changed}")
    if signals:
        post_signals(signals)
    return 0


def cmd_news(args: argparse.Namespace) -> int:
    path, count = news_mod.run()
    print(f"news saved: {path} ({count} items)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch listings from sources")
    p_fetch.add_argument("--source", dest="sources", action="append", help="source name (repeatable)")
    p_fetch.add_argument("--dry-run", action="store_true", help="print JSON, don't write snapshot")
    p_fetch.set_defaults(func=cmd_fetch)

    p_notify = sub.add_parser("notify", help="Detect buy signals and post to Slack")
    p_notify.add_argument("--test", action="store_true", help="send a fabricated signal for webhook smoke test")
    p_notify.set_defaults(func=cmd_notify)

    p_render = sub.add_parser("render", help="Render static dashboard into ./site")
    p_render.set_defaults(func=cmd_render)

    p_watch = sub.add_parser("watch", help="Sub-daily Apple-refurb watcher (dedup'd alerts)")
    p_watch.set_defaults(func=cmd_watch)

    p_news = sub.add_parser("news", help="Fetch Mac mini related news (Google News RSS)")
    p_news.set_defaults(func=cmd_news)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
