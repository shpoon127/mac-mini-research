from __future__ import annotations

import json
from pathlib import Path

from .analyze import BuySignal
from .models import Listing
from .scrapers import apple_refurb
from .storage import DATA_DIR

APPLE_SEEN_FILE = DATA_DIR / "apple_seen.json"


def _load_seen() -> dict:
    if not APPLE_SEEN_FILE.exists():
        return {}
    return json.loads(APPLE_SEEN_FILE.read_text())


def _save_seen(seen: dict) -> None:
    APPLE_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    APPLE_SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2, sort_keys=True))


def _record(listing: Listing, today: str) -> dict:
    return {
        "first_seen": today,
        "title": listing.title,
        "memory_gb": listing.memory_gb,
        "storage_gb": listing.storage_gb,
        "price_jpy": listing.price_jpy,
        "url": listing.url,
    }


def diff_new(fetched: list[Listing], seen: dict, today: str) -> tuple[list[BuySignal], dict]:
    """Return (signals_for_new_skus, updated_seen_dict). seen is not mutated."""
    updated = dict(seen)
    signals: list[BuySignal] = []
    for l in fetched:
        if not l.sku or l.sku in updated:
            continue
        updated[l.sku] = _record(l, today)
        signals.append(
            BuySignal(
                kind="new_refurb_in_stock",
                source=l.source,
                memory_gb=l.memory_gb,
                title=l.title,
                price_jpy=l.price_jpy,
                url=l.url,
            )
        )
    return signals, updated


def run(today: str) -> tuple[list[BuySignal], bool]:
    """Fetch Apple refurb, diff against persisted seen-set, return (new_signals, changed)."""
    fetched = apple_refurb.fetch()
    seen = _load_seen()
    signals, updated = diff_new(fetched, seen, today)
    changed = updated != seen
    if changed:
        _save_seen(updated)
    return signals, changed
