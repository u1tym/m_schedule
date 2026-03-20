# m_schedule FastAPI

## セットアップ

1. 依存パッケージをインストールする

```bash
pip install -r requirements.txt
```

2. PostgreSQL 接続を設定する（必須）。サンプルをコピーし、実際のサーバーに合わせて値を編集する。

```bash
cp .env.example .env
```

Pydantic は `DB_SERVER`、`DB_PORT`、`DB_NAME`、`DB_USERNAME`、`DB_PASSWORD` を読み取ります（詳細は `.env.example` を参照）。`.env` またはこれらの環境変数が無いと、インポート時にバリデーションエラーで起動に失敗します。

3. API を起動する

```bash
uvicorn app.main:app --reload
```

## ログ

- **出力先**: プロジェクトルートからの相対パス `logs/`（既定）。`.env` の `LOG_DIR` で変更できます。起動時にフォルダが無ければ作成されます。
- **ファイル**: `logs/app.log` に追記。`TimedRotatingFileHandler` により **毎日 0 時** にローテーションし、古いファイルは `app.log.YYYY-MM-DD` 形式で残ります。
- **保持数**: 既定で直近 30 個（`LOG_BACKUP_COUNT`）。
- **レベル**: 既定 `INFO`（`LOG_LEVEL` で `DEBUG` などに変更可）。
- **記録内容**
  - 各リクエスト: メソッド・パス・クエリ・クライアント IP、応答ステータス、処理時間（ms）
  - HTTP 4xx / 5xx: 上記に加え警告・エラーレベルで記録
  - `HTTPException`: ステータス・`detail`・リクエスト行
  - バリデーションエラー（422）: エラー内容・リクエストボディ（`RequestValidationError`）
  - 未処理例外: スタックトレース付き

## API ドキュメント

- Swagger UI: `http://localhost:8000/docs`
