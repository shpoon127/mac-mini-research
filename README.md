# Mac mini M4 Price Tracker

M4 Mac mini (24GB / 32GB) の新品・中古を毎日チェックして「買い時」をダッシュボード+Slack通知で知るためのリサーチ用ツール。

> **本ツールについて**: 個人利用目的の低頻度ウォッチャーです。価格情報の収集は公開ページの参照に留め、頻度を抑えて運用しています（日次バッチ + Apple整備済のみ1時間毎）。各サイト運営者から削除・停止のご要望があれば速やかに対応します。

## 監視対象

| ソース | 区分 | 状態 |
| --- | --- | --- |
| Apple整備済 (`apple_refurb`) | 新品(整備済) | 実装済 (JSON-LD パース) |
| イオシス (`iosys`) | 中古 | 実装済 (HTML パース) |
| じゃんぱら | 中古 | 保留 (JSレンダリングで未実装) |
| Amazon | 新品 | 未実装 |

## 通知トリガ

- **整備済品 新規入荷**: Apple整備済ページに今まで見ていないSKUの対象モデルが出現
- **30日内最安値割れ**: (source, memory_gb) 単位で過去30日の最安値より低い

## 使い方

```bash
uv sync
uv run tracker fetch          # スクレイプ → data/ に保存
uv run tracker notify         # buy signal 検出 → Slack 送信
uv run tracker render         # site/ に静的ダッシュボード生成
uv run pytest                 # テスト
```

環境変数: `SLACK_WEBHOOK_URL` (未設定なら標準出力にプレビュー)

## CI

`.github/workflows/daily.yml` が毎日 07:00 JST に実行され、
1. スクレイプ → `data/` にコミット
2. buy signal を Slack 通知
3. `site/` を GitHub Pages にデプロイ

## 構造

```
src/tracker/
  scrapers/        # サイトごとのフェッチ&パース
  models.py        # Listing dataclass
  storage.py       # JSON/JSONL 永続化
  analyze.py       # buy signal 検出
  notify.py        # Slack webhook
  render.py        # 静的ダッシュボード生成
  cli.py           # `tracker` コマンド
```
