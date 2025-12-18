# 補助金ポータル スクレイパー

福井県の補助金ポータル（https://hojyokin-portal.jp/subsidies/list?pref_id=18）から
補助金情報をスクレイピングしてJSON形式で保存するツールです。

## 機能

- 全ページの自動取得（ページネーション対応）
- サーバー負荷軽減のためのリクエスト間隔調整
- JSON形式での出力

## インストール

```bash
cd src/subsidy_scraper
pip install -r requirements.txt
```

## 使用方法

### 基本的な使い方

```bash
python scraper.py
```

### オプション

```bash
# 最大5ページまで取得
python scraper.py --max-pages 5

# リクエスト間隔を2秒に設定
python scraper.py --delay 2.0

# 出力ファイルを指定
python scraper.py --output ./data/subsidies.json

# 別の都道府県を指定（例: 東京都=13）
python scraper.py --pref-id 13
```

### Pythonコードから使用

```python
from scraper import SubsidyScraper

# スクレイパーを初期化（福井県、リクエスト間隔1秒）
scraper = SubsidyScraper(pref_id=18, delay=1.0)

# 全ページから補助金情報を取得
subsidies = scraper.scrape_all()

# JSONファイルに保存
output_path = scraper.save_to_json(subsidies)
print(f"保存先: {output_path}")
```

## 出力形式

JSONファイルは以下の形式で出力されます：

```json
{
  "metadata": {
    "source": "https://hojyokin-portal.jp/subsidies/list",
    "prefecture_id": 18,
    "scraped_at": "2025-12-16T10:00:00",
    "total_count": 831
  },
  "subsidies": [
    {
      "status": "公募中",
      "title": "プラスチック代替製品利用促進補助金",
      "url": "https://hojyokin-portal.jp/subsidies/...",
      "prefecture": "福井県",
      "application_period": "2025年4月1日〜2026年2月27日",
      "start_date": "2025年4月1日",
      "end_date": "2026年2月27日",
      "max_amount": "30万円",
      "description": "県内事業者等によるプラスチック代替製品の導入...",
      "tags": ["#飲食業", "#宿泊施設", "#飲食店"]
    }
  ]
}
```

## 注意事項

- スクレイピングはサーバーに負荷をかける可能性があります。`--delay`オプションで適切な間隔を設定してください。
- ウェブサイトの構造が変更された場合、スクレイピングが正常に動作しなくなる可能性があります。
- 利用規約を確認の上、適切にご使用ください。

## 都道府県ID一覧

| ID | 都道府県 | ID | 都道府県 |
|----|----------|----|---------| 
| 1  | 北海道   | 25 | 滋賀県   |
| 13 | 東京都   | 26 | 京都府   |
| 14 | 神奈川県 | 27 | 大阪府   |
| 18 | 福井県   | 28 | 兵庫県   |
| 23 | 愛知県   | 40 | 福岡県   |

