from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .models import Listing

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
HISTORY_FILE = DATA_DIR / "history.jsonl"
LATEST_FILE = DATA_DIR / "latest.json"


def _ensure_dirs() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def save_snapshot(listings: list[Listing]) -> Path:
    _ensure_dirs()
    today = date.today().isoformat()
    path = SNAPSHOTS_DIR / f"{today}.json"
    payload = {
        "date": today,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "listings": [l.to_dict() for l in listings],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        for l in listings:
            f.write(json.dumps({"date": today, **l.to_dict()}, ensure_ascii=False) + "\n")

    LATEST_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    with HISTORY_FILE.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_previous_snapshot() -> dict | None:
    if not SNAPSHOTS_DIR.exists():
        return None
    files = sorted(SNAPSHOTS_DIR.glob("*.json"))
    today = date.today().isoformat()
    prior = [p for p in files if p.stem != today]
    if not prior:
        return None
    return json.loads(prior[-1].read_text())


def lowest_in_window(history: list[dict], source: str, memory_gb: int, days: int) -> int | None:
    cutoff = date.today() - timedelta(days=days)
    prices = [
        row["price_jpy"]
        for row in history
        if row.get("source") == source
        and row.get("memory_gb") == memory_gb
        and date.fromisoformat(row["date"]) >= cutoff
    ]
    return min(prices) if prices else None
