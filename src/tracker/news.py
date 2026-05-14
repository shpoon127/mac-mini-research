"""Mac mini 関連ニュースを Google News RSS から取得する。

在庫枯渇・新品価格高騰など、ダッシュボード閲覧時の文脈情報として表示するためのもの。
依存追加なしで stdlib (xml.etree, urllib) のみで動かす。
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import USER_AGENT

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
NEWS_FILE = DATA_DIR / "news.json"

# Google News RSS endpoint. ja-JP に固定。
RSS_BASE = "https://news.google.com/rss/search"

# 「在庫枯渇・新品価格高騰」を主眼にしたクエリ群。
# 重複排除は URL/タイトルで後段で行う。
QUERIES: tuple[str, ...] = (
    "Mac mini M4 在庫",
    "Mac mini 値上げ",
    "Mac mini 価格改定",
    "Mac mini M4",
    "Apple 整備済 Mac mini",
)

MAX_ITEMS_PER_QUERY = 10
MAX_TOTAL_ITEMS = 30
TIMEOUT_SEC = 20

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class NewsItem:
    title: str
    url: str
    source: str  # 配信元 (例: "ITmedia NEWS")
    published: str  # ISO8601 UTC
    query: str  # どのクエリで拾ったか


def _build_url(query: str) -> str:
    params = {"q": query, "hl": "ja", "gl": "JP", "ceid": "JP:ja"}
    return f"{RSS_BASE}?{urllib.parse.urlencode(params)}"


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_pubdate(value: str | None) -> str:
    # RFC822: "Mon, 12 May 2026 09:00:00 GMT"
    if not value:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            continue
    return value


def _fetch_rss(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_items(xml_text: str, query: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    root = ET.fromstring(xml_text)
    # RSS 2.0: rss/channel/item
    for it in root.iterfind("./channel/item"):
        title = _strip_tags((it.findtext("title") or ""))
        link = (it.findtext("link") or "").strip()
        pub = _parse_pubdate(it.findtext("pubDate"))
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None and src_el.text else ""
        if not title or not link:
            continue
        items.append(NewsItem(title=title, url=link, source=source, published=pub, query=query))
        if len(items) >= MAX_ITEMS_PER_QUERY:
            break
    return items


def fetch_news() -> list[NewsItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    all_items: list[NewsItem] = []
    for q in QUERIES:
        try:
            xml_text = _fetch_rss(_build_url(q))
        except Exception as e:  # ネット不調等は無視して他クエリへ
            print(f"[news] query={q!r} error: {e!r}")
            continue
        try:
            items = _parse_items(xml_text, q)
        except ET.ParseError as e:
            print(f"[news] parse error for {q!r}: {e!r}")
            continue
        for item in items:
            if item.url in seen_urls or item.title in seen_titles:
                continue
            seen_urls.add(item.url)
            seen_titles.add(item.title)
            all_items.append(item)

    all_items.sort(key=lambda x: x.published, reverse=True)
    return all_items[:MAX_TOTAL_ITEMS]


def save(items: list[NewsItem]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "queries": list(QUERIES),
        "items": [asdict(i) for i in items],
    }
    NEWS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return NEWS_FILE


def run() -> tuple[Path, int]:
    items = fetch_news()
    path = save(items)
    return path, len(items)
