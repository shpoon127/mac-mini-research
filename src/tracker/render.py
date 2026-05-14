from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .storage import HISTORY_FILE, LATEST_FILE

ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "site"
SITE_TEMPLATE = SITE_DIR / "index.html"
SITE_DATA = SITE_DIR / "data.json"
NEWS_FILE = ROOT / "data" / "news.json"


def _build_payload() -> dict:
    history: list[dict] = []
    if HISTORY_FILE.exists():
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            history = [json.loads(line) for line in f if line.strip()]

    latest: dict = {}
    if LATEST_FILE.exists():
        latest = json.loads(LATEST_FILE.read_text())

    # Daily minimum price per (source, memory_gb)
    series: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    # Daily stock count per (source, memory_gb) — 在庫枯渇トレンド可視化用
    stock: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    for row in history:
        d = row.get("date")
        src = row.get("source")
        mem = row.get("memory_gb")
        price = row.get("price_jpy")
        if not (d and src and mem and price):
            continue
        key = f"{mem}GB"
        cur = series[src][key].get(d)
        if cur is None or price < cur:
            series[src][key][d] = price
        stock[src][key][d] = stock[src][key].get(d, 0) + 1

    news: dict = {}
    if NEWS_FILE.exists():
        try:
            news = json.loads(NEWS_FILE.read_text())
        except json.JSONDecodeError:
            news = {}

    return {
        "generated_at": latest.get("fetched_at"),
        "today": latest.get("date"),
        "listings": latest.get("listings", []),
        "series": series,
        "stock": stock,
        "news": news,
    }


def render() -> Path:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    payload = _build_payload()
    SITE_DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    if not SITE_TEMPLATE.exists():
        SITE_TEMPLATE.write_text(_default_template())
    return SITE_TEMPLATE


# NOTE: site/index.html がリポジトリにコミットされている前提なので、
# _default_template はブートストラップ用フォールバック。
# UI を変える場合は site/index.html を直接編集する。


def _default_template() -> str:
    return r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Mac mini M4 価格トラッカー</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
         max-width: 980px; margin: 2rem auto; padding: 0 1rem; color: #222; }
  h1 { font-size: 1.4rem; }
  h2 { font-size: 1.1rem; margin-top: 2rem; }
  .muted { color: #888; font-size: 0.85rem; }
  table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
  th, td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; text-align: left; }
  th { background: #fafafa; }
  .source { display: inline-block; padding: 0 0.4rem; border-radius: 4px;
            font-size: 0.75rem; background: #eef; color: #225; }
  .empty { padding: 1rem; background: #f7f7f7; border-radius: 6px; color: #666; }
  canvas { max-height: 320px; }
</style>
</head>
<body>
  <h1>Mac mini M4 価格トラッカー <span id="today" class="muted"></span></h1>
  <p class="muted">対象: M4 Mac mini (24GB / 32GB) — 新品 (Apple整備済) / 中古 (イオシス)</p>

  <h2>今日の在庫</h2>
  <div id="listings"></div>

  <h2>価格推移 (日次最安値)</h2>
  <canvas id="chart"></canvas>

  <p class="muted" id="generated"></p>

<script>
async function main() {
  const data = await fetch('data.json').then(r => r.json());
  document.getElementById('today').textContent = data.today ? `(${data.today})` : '';
  const fmtJst = (iso) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const parts = new Intl.DateTimeFormat('ja-JP', {
      timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d).reduce((a, p) => (a[p.type] = p.value, a), {});
    return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute} JST`;
  };
  document.getElementById('generated').textContent = data.generated_at
    ? `更新: ${fmtJst(data.generated_at)}` : '';

  // listings table
  const listings = data.listings || [];
  const root = document.getElementById('listings');
  if (!listings.length) {
    root.innerHTML = '<div class="empty">該当する在庫はありません</div>';
  } else {
    const rows = listings.map(l => `
      <tr>
        <td><span class="source">${l.source}</span></td>
        <td>${l.memory_gb ?? '?'}GB</td>
        <td>${l.storage_gb ?? '?'}GB</td>
        <td>¥${(l.price_jpy ?? 0).toLocaleString()}</td>
        <td><a href="${l.url}" target="_blank" rel="noopener">${l.title}</a></td>
      </tr>`).join('');
    root.innerHTML = `<table>
      <thead><tr><th>ソース</th><th>メモリ</th><th>ストレージ</th><th>価格</th><th>タイトル</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  }

  // chart: build datasets per (source, memory)
  const series = data.series || {};
  const datasets = [];
  const palette = {
    apple_refurb_24GB: '#0a84ff', apple_refurb_32GB: '#3399ff',
    iosys_24GB:        '#ff6b35', iosys_32GB:        '#ffa07a',
    amazon_24GB:       '#34c759', amazon_32GB:       '#7fdc8a',
  };
  const allDates = new Set();
  for (const src of Object.keys(series)) {
    for (const mem of Object.keys(series[src])) {
      const points = series[src][mem];
      for (const d of Object.keys(points)) allDates.add(d);
      const label = `${src} ${mem}`;
      const color = palette[`${src}_${mem}`] || '#888';
      datasets.push({
        label, points,
        borderColor: color, backgroundColor: color, tension: 0.2, spanGaps: true,
      });
    }
  }
  const dates = [...allDates].sort();
  for (const ds of datasets) {
    ds.data = dates.map(d => ds.points[d] ?? null);
    delete ds.points;
  }

  new Chart(document.getElementById('chart'), {
    type: 'line',
    data: { labels: dates, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      scales: { y: { ticks: { callback: v => '¥' + v.toLocaleString() } } },
    },
  });
}
main();
</script>
</body>
</html>
"""
