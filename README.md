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

## API ドキュメント

- Swagger UI: `http://localhost:8000/docs`
