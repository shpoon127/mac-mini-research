from __future__ import annotations

import re

import httpx
from selectolax.parser import HTMLParser

from ..config import USER_AGENT
from ..models import Listing

URL = "https://iosys.co.jp/items/deskpc/mac/apple"

# Title examples:
#   "Mac mini MU9D3J/A 2024【Apple M4(8GB)/10コアGPU/256GB SSD】"
#   "Mac mini MU9E3J/A 2024【Apple M4(24GB)/10コアGPU/512GB SSD】"
#   "Mac mini MRTR2J/A Late 2018【Core i3(3.6GHz)/8GB/256GB SSD】"
MEMORY_RE = re.compile(r"\((\d+)GB\)")  # iosys puts memory inside chip parens
STORAGE_RE = re.compile(r"(\d+)\s*(TB|GB)\s*SSD")
PRICE_RE = re.compile(r"([\d,]+)")


def _parse_memory(title: str) -> int | None:
    m = MEMORY_RE.search(title)
    return int(m.group(1)) if m else None


def _parse_storage(title: str) -> int | None:
    m = STORAGE_RE.search(title)
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    return value * 1024 if unit == "TB" else value


def _is_target(title: str) -> bool:
    if "Mac mini" not in title:
        return False
    # iosys lists M-series in the chip section as "Apple M4" / "Apple M4 Pro"
    if "M4 Pro" in title or "M4 Max" in title:
        return False
    if "M4" not in title:
        return False
    mem = _parse_memory(title)
    return mem in (24, 32)


def parse(html: str) -> list[Listing]:
    tree = HTMLParser(html)
    listings: list[Listing] = []
    seen: set[str] = set()

    for li in tree.css("li"):
        link = li.css_first("a[href^='/items/deskpc/mac/apple/']")
        if not link:
            continue
        href = link.attributes.get("href", "")
        if href in seen:
            continue

        name_node = li.css_first("p.name")
        price_node = li.css_first("div.price p")
        if not name_node or not price_node:
            continue

        title = name_node.text(strip=True)
        if not _is_target(title):
            continue

        price_match = PRICE_RE.search(price_node.text())
        if not price_match:
            continue
        price = int(price_match.group(1).replace(",", ""))

        cond_node = li.css_first("p.condition")
        condition_label = cond_node.text(strip=True) if cond_node else "used"

        seen.add(href)
        listings.append(
            Listing(
                source="iosys",
                condition="used",
                title=f"{title} [{condition_label}]",
                chip="M4",
                memory_gb=_parse_memory(title),
                storage_gb=_parse_storage(title),
                price_jpy=price,
                url=f"https://iosys.co.jp{href}",
                sku=href.rstrip("/").rsplit("/", 1)[-1],
            )
        )
    return listings


def fetch(client: httpx.Client | None = None) -> list[Listing]:
    owns = client is None
    if owns:
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
        if owns:
            client.close()
