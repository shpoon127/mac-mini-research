from __future__ import annotations

import json
import re
from typing import Iterable

import httpx

from ..config import TARGET_CHIP, TARGET_MEMORY_GB, USER_AGENT
from ..models import Listing

URL = "https://www.apple.com/jp/shop/refurbished/mac"

# Apple integrates structured data per product via <script type="application/ld+json">
JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>',
    re.DOTALL,
)

# Name examples (assumed when in stock):
#   "Mac mini（M4チップ、24GB、512GB SSD）[整備済製品]"
#   "Mac mini Apple M4 Proチップ、48GB、1TB SSD [整備済製品]"
MEMORY_RE = re.compile(r"(\d+)\s*GB")
STORAGE_RE = re.compile(r"(\d+)\s*(TB|GB)\s*SSD")


def _parse_storage(name: str) -> int | None:
    m = STORAGE_RE.search(name)
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    return value * 1024 if unit == "TB" else value


def _parse_memory(name: str) -> int | None:
    # First GB-occurrence in "...M4チップ、24GB、512GB SSD..." is memory.
    # We rely on memory always preceding storage.
    for m in MEMORY_RE.finditer(name):
        gb = int(m.group(1))
        # storage values are typically >=256, memory is <=128. Anything <=128 is memory.
        if gb <= 128:
            return gb
    return None


def _is_target(product: dict) -> bool:
    name = product.get("name", "")
    if "Mac mini" not in name:
        return False
    if TARGET_CHIP not in name:
        return False
    # Exclude "M4 Pro" / "M4 Max" — match only base M4.
    if "M4 Pro" in name or "M4 Max" in name:
        return False
    mem = _parse_memory(name)
    return mem in TARGET_MEMORY_GB


def _to_listing(product: dict) -> Listing | None:
    name = product["name"]
    offers = product.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price")
    if price is None:
        return None
    return Listing(
        source="apple_refurb",
        condition="refurb",
        title=name,
        chip=TARGET_CHIP,
        memory_gb=_parse_memory(name),
        storage_gb=_parse_storage(name),
        price_jpy=int(price),
        url=product.get("url", URL),
        sku=offers.get("sku") or product.get("sku"),
    )


def parse(html: str) -> list[Listing]:
    listings: list[Listing] = []
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "Product":
            continue
        if not _is_target(data):
            continue
        item = _to_listing(data)
        if item is not None:
            listings.append(item)
    return listings


def fetch(client: httpx.Client | None = None) -> list[Listing]:
    owns_client = client is None
    if owns_client:
        client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"},
            timeout=30.0,
            follow_redirects=True,
        )
    try:
        resp = client.get(URL)
        resp.raise_for_status()
        return parse(resp.text)
    finally:
        if owns_client:
            client.close()
