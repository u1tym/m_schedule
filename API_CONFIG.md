# DB・API 仕様（config.value）

## データベース

- **RDBMS**: PostgreSQL
- **スキーマ**: `config`
- **テーブル**: `config.value`

| カラム    | 型   | 説明                         |
|-----------|------|------------------------------|
| `id`      | int  | ユーザ ID。`0` は共通ユーザ |
| `keyword` | text | 設定項目名                   |
| `value`   | text | 設定値                       |

- **主キー**: `(id, keyword)`

DDL の例は `db/db.sql` を参照してください。

## 接続設定（.env）

アプリはプロジェクトルートの `.env` から次の変数を読み込みます（環境変数でも上書き可）。

| 変数名             | 意味     | 初期値例   |
|--------------------|----------|------------|
| `POSTGRES_HOST`    | ホスト   | localhost  |
| `POSTGRES_PORT`    | ポート   | 5432       |
| `POSTGRES_DB`      | DB 名    | tamtdb     |
| `POSTGRES_USER`    | ユーザ名 | tamtuser   |
| `POSTGRES_PASSWORD`| パスワード | （.env 参照） |

内部的には `postgresql+asyncpg://...` 形式の URL に変換して接続します。

## ドメインルール

- **`id = 0`**: 共通ユーザ。本 API はこの ID の行のみを扱います。
- **`keyword`**: 設定キー（項目名）。
- **`value`**: 設定内容（文字列）。

## 想定している keyword / value（現時点）

### `calender-monthly-type`

月次表示の形式。

| value  | 意味                               |
|--------|------------------------------------|
| `box`  | 月次表示ではカレンダー表示にする   |
| `list` | 月次表示ではリスト形式で表示する   |

### `calender-weekly-start`

週の開始曜日（カレンダー表示時）。

| value    | 意味                         |
|----------|------------------------------|
| `sunday` | 日曜始まりで表示する         |
| `monday` | 月曜始まりで表示する         |

（スペルは DB・仕様どおり `calender` としています。）

## HTTP API

ベース URL はデプロイに依存します。ローカル例: `http://localhost:8000`。

### 1) 設定値取得

- **メソッド・パス**: `GET /settings`
- **処理**: `config.value` から `id = 0` の行をすべて取得し、次の JSON オブジェクトで返す。
  - キー: `keyword`
  - 値: `value`

**レスポンス例**

```json
{
  "calender-monthly-type": "box",
  "calender-weekly-start": "sunday"
}
```

（キー名・件数は DB の内容に依存します。）

### 2) 設定値更新

- **メソッド・パス**: `PUT /settings`
- **Content-Type**: `application/json`
- **リクエストボディ**: 先頭に `id` を必須とし、**`id` は必ず `0`**。それ以外のプロパティは「設定キー → 文字列値」として扱い、複数指定可。

**リクエスト例**

```json
{
  "id": 0,
  "calender-monthly-type": "list",
  "calender-weekly-start": "monday"
}
```

- **`id` が `0` 以外**: `400 Bad Request`。メッセージで異常であることを示す。
- **`id` のみでキーがない**: `422 Unprocessable Entity`（更新対象なし）。

**更新の意味**

- 指定された各キーについて、`(id, keyword) = (0, キー)` の行があれば `value` を更新する。
- まだ行がないキーは **新規に挿入** する（PostgreSQL の `ON CONFLICT DO UPDATE` による upsert）。

**レスポンス例（成功時）**

```json
{
  "updated": 2,
  "id": 0
}
```

### その他

- **ヘルスチェック**: `GET /health` — `{"status":"ok"}` を返す。

## OpenAPI

アプリ起動後、対話ドキュメントは `/docs`（Swagger UI）、`/redoc`（ReDoc）で確認できます。
