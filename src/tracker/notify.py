from __future__ import annotations

import json
import os
import urllib.request

from .analyze import BuySignal


def _format(signal: BuySignal) -> str:
    yen = f"¥{signal.price_jpy:,}"
    mem = f"{signal.memory_gb}GB" if signal.memory_gb else "?GB"
    if signal.kind == "new_refurb_in_stock":
        head = f":sparkles: Apple整備済品に入荷 — Mac mini M4 / {mem} / {yen}"
    elif signal.kind == "new_window_low":
        prev = f"¥{signal.prev_low_jpy:,}" if signal.prev_low_jpy else "n/a"
        head = (
            f":chart_with_downwards_trend: {signal.source} で {signal.window_days}日内の最安値更新 — "
            f"Mac mini M4 / {mem} / {yen} (前最安 {prev})"
        )
    else:
        head = f"{signal.kind}: {mem} {yen}"
    return f"{head}\n{signal.title}\n{signal.url}"


def post(signals: list[BuySignal], webhook_url: str | None = None) -> int:
    if not signals:
        return 0
    webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[notify] SLACK_WEBHOOK_URL not set; would have sent:")
        for s in signals:
            print(_format(s))
            print("---")
        return 0

    text = "\n\n".join(_format(s) for s in signals)
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status
