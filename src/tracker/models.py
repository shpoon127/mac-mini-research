from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class Listing:
    source: str          # apple_refurb | amazon | iosys | janpara
    condition: str       # new | refurb | used
    title: str
    chip: str            # M4 / M4 Pro / unknown
    memory_gb: int | None
    storage_gb: int | None
    price_jpy: int
    url: str
    sku: str | None = None
    fetched_at: str = ""

    def __post_init__(self) -> None:
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        return asdict(self)

    def key(self) -> str:
        return f"{self.source}:{self.sku or self.url}"
