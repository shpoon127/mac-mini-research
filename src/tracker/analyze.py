from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from .config import LOWEST_WINDOW_DAYS


@dataclass
class BuySignal:
    kind: str            # "new_refurb_in_stock" | "new_window_low"
    source: str
    memory_gb: int | None
    title: str
    price_jpy: int
    url: str
    prev_low_jpy: int | None = None
    window_days: int | None = None


def _key(row: dict) -> tuple:
    return (row.get("source"), row.get("memory_gb"))


def detect_signals(today_listings: list[dict], history: list[dict]) -> list[BuySignal]:
    """Compare today's listings against the prior window to find buy signals.

    Signals:
      - new_refurb_in_stock: an apple_refurb listing that wasn't in any prior snapshot.
      - new_window_low: today's price is strictly lower than the min over the prior N days
        (excluding today), per (source, memory_gb).
    """
    signals: list[BuySignal] = []
    today_str = date.today().isoformat()
    prior = [r for r in history if r.get("date") != today_str]

    # 1) Apple refurb new entries: SKU not seen before
    prior_apple_skus = {
        r.get("sku") for r in prior if r.get("source") == "apple_refurb" and r.get("sku")
    }
    for row in today_listings:
        if row.get("source") != "apple_refurb":
            continue
        if row.get("sku") and row["sku"] in prior_apple_skus:
            continue
        signals.append(
            BuySignal(
                kind="new_refurb_in_stock",
                source=row["source"],
                memory_gb=row.get("memory_gb"),
                title=row.get("title", ""),
                price_jpy=row.get("price_jpy", 0),
                url=row.get("url", ""),
            )
        )

    # 2) Window-low: min over prior N days by (source, memory_gb)
    cutoff = date.today() - timedelta(days=LOWEST_WINDOW_DAYS)
    window_min: dict[tuple, int] = defaultdict(lambda: 10**12)
    for r in prior:
        try:
            d = date.fromisoformat(r["date"])
        except (KeyError, ValueError):
            continue
        if d < cutoff:
            continue
        price = r.get("price_jpy")
        if price is None:
            continue
        k = _key(r)
        if price < window_min[k]:
            window_min[k] = price

    today_min: dict[tuple, dict] = {}
    for row in today_listings:
        k = _key(row)
        price = row.get("price_jpy")
        if price is None:
            continue
        cur = today_min.get(k)
        if cur is None or price < cur["price_jpy"]:
            today_min[k] = row

    for k, row in today_min.items():
        prev = window_min.get(k)
        if prev is None or prev == 10**12:
            continue
        if row["price_jpy"] < prev:
            signals.append(
                BuySignal(
                    kind="new_window_low",
                    source=row["source"],
                    memory_gb=row.get("memory_gb"),
                    title=row.get("title", ""),
                    price_jpy=row["price_jpy"],
                    url=row.get("url", ""),
                    prev_low_jpy=prev,
                    window_days=LOWEST_WINDOW_DAYS,
                )
            )

    return signals
