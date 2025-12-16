# 補助金検索アプリ

Jグランツ公開APIを使用して、条件に合致する補助金一覧を検索・表示するWebアプリケーションです。

## 概要

このアプリケーションは、[デジタル庁 Jグランツ API](https://developers.digital.go.jp/documents/jgrants/api/)を活用し、以下の条件で補助金を検索できます：

- キーワード検索
- 対象地域
- 補助金上限額
- 対象従業員数
- 利用目的
- 受付中のみ表示

## インストール方法

```bash
cd src
pip install -r requirements.txt
```

## 使用方法

### アプリケーションの起動

```bash
cd src
python subsidy_search.py
```

起動後、ブラウザで `http://127.0.0.1:5000` にアクセスしてください。

### 検索方法

1. 検索条件を入力（すべて任意）
2. 「検索する」ボタンをクリック
3. 結果一覧から「詳細を見る」で補助金の詳細情報を確認

## ファイル構成

```
src/
├── subsidy_search.py          # エントリーポイント
├── subsidy_search_lib/        # メインパッケージ
│   ├── __init__.py            # パッケージ初期化
│   ├── config.py              # 設定・定数
│   ├── api_client.py          # Jグランツ APIクライアント
│   ├── main.py                # Flaskアプリケーション
│   ├── templates/             # HTMLテンプレート
│   │   └── index.html
│   └── static/                # 静的ファイル
│       └── style.css
└── requirements.txt           # 依存パッケージ
```

## カスタマイズ方法

### ポート番号の変更

`src/subsidy_search_lib/config.py` の以下の値を変更：

```python
FLASK_PORT = 5000  # 希望のポート番号に変更
```

### APIタイムアウトの変更

同じく `config.py` で変更可能：

```python
API_TIMEOUT = 30  # 秒数を変更
```

## 注意事項

- Jグランツ APIの利用規約に従ってご利用ください
- APIの仕様変更により動作しなくなる場合があります
- 本番環境での利用時は `FLASK_DEBUG = False` に設定してください

## データ出典

- [デジタル庁 Jグランツ APIドキュメント](https://developers.digital.go.jp/documents/jgrants/api/)

## 改訂履歴

| 日付 | 版 | 内容 |
|------|-----|------|
| 2024-12-16 | 1.0 | 初版作成 |
