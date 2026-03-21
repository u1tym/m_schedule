# m_schedule データベース構成と API 仕様

## 1. 環境変数

API は DB 接続設定を `.env` から読み取ります。

```env
DB_SERVER=localhost
DB_PORT=5432
DB_NAME=tamtdb
DB_USERNAME=tamtuser
DB_PASSWORD=TAMTTAMT
```

接続文字列の形式:

`postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}`

（ログ用の任意項目 `LOG_DIR` / `LOG_LEVEL` / `LOG_BACKUP_COUNT` については README を参照。）

## 2. データベース構成

### 2.1 `activity_categories`

- 用途: スケジュールのカテゴリマスタ。
- カラム:
  - `id`: integer, PK
  - `name`: varchar, not null
  - `is_deleted`: boolean, not null（論理削除）
  - `created_at`: timestamp, not null, 既定 `now()`
  - `updated_at`: timestamp, not null, 既定 `now()`

### 2.2 `holidays`

- 用途: 祝日など（週末以外の休日と名称）。
- カラム:
  - `id`: integer, PK
  - `date`: date, not null, unique
  - `name`: varchar, not null
  - `created_at`: timestamp, nullable
  - `updated_at`: timestamp, nullable

### 2.3 `schedules`

- 用途: スケジュールおよび TODO。
- カラム:
  - `id`: integer, PK
  - `title`: varchar, not null
  - `start_datetime`: timestamp, not null
  - `duration`: integer, not null
  - `is_all_day`: boolean, not null
  - `activity_category_id`: integer, FK → `activity_categories.id`
  - `schedule_type`: varchar, not null（`"予定"` または `"TODO"`）
  - `location`: varchar, nullable
  - `details`: text, nullable
  - `is_todo_completed`: boolean, not null
  - `is_deleted`: boolean, not null（論理削除）
  - `created_at`: timestamp, not null, 既定 `now()`
  - `updated_at`: timestamp, not null, 既定 `now()`

## 3. 業務ルール

### 3.1 終日スケジュール

- `is_all_day = true`
- `start_datetime` は `00:00:00` であること
- `duration` は日数
- 終了日 = 開始日 + (`duration` - 1) 日

### 3.2 分単位スケジュール

- `is_all_day = false`
- `start_datetime` は日付と時刻を含み、秒は `00` であること
- `duration` は分
- 終了日時 = 開始日時 + `duration` 分

### 3.3 TODO の扱い

- `schedule_type` は `"予定"` または `"TODO"`
- `is_todo_completed` は `"TODO"` のときに意味を持つ

## 4. API エンドポイント

ベース URL の例: `http://localhost:8000`

### 4.1 活動カテゴリ

1. `GET /activity-categories`
   - 論理削除されていないカテゴリ一覧を返す。

2. `POST /activity-categories`
   - リクエストボディ例:
     ```json
     {
       "name": "会議"
     }
     ```

3. `DELETE /activity-categories/{category_id}`
   - 論理削除（`is_deleted = true`）。

### 4.2 祝日

4. `GET /holidays?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
   - 両方のクエリは任意。
   - 省略時は全祝日。
   - 指定時は両端を含む範囲で返す。

5. `POST /holidays`
   - リクエストボディ例:
     ```json
     {
       "date": "2026-01-01",
       "name": "元日"
     }
     ```

### 4.3 スケジュール

6. `GET /schedules?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
   - 必須: `from_date`, `to_date`
   - 次の期間と重なるスケジュールを返す:
     - `from_date` の `00:00` から `to_date` の `23:59` まで（両端含む）
   - レスポンスの各要素に含まれるもの:
     - `id`
     - `title`
     - `activity_category_id`
     - `activity_category_name`
     - `is_all_day`
     - 終日: `start_date`, `end_date`
     - 分単位: `start_datetime`, `end_datetime`
     - `schedule_type`（`"予定"` または `"TODO"`）
     - TODO の場合: `is_todo_completed`

7. `GET /schedules/todo-alerts?ref_date=YYYY-MM-DD`
   - **注意喚起対象 TODO 取得**（`schedule_type` が `"TODO"` の行のみ。`"予定"` は返さない）。
   - 必須: `ref_date`（基準日。当日などを指定する想定）
   - **返す条件**（いずれかに該当し、かつ削除済みカテゴリに紐づく行は除外。論理削除済みスケジュールも除外）:
     1. **過去の未完了**: 占有区間の開始が基準日の `00:00` より前で、かつ `is_todo_completed` が false。
     2. **基準日からのウィンドウ**: 占有区間が、基準日 `00:00` から **基準日 + 3 日** の `23:59` まで（基準日を含む **4 暦日**）と重なる。完了・未完了の両方を含む。
   - 占有区間の計算は `GET /schedules` と同じ（終日は日単位、分単位は分で加算）。
   - レスポンスの各要素:
     - `id`（スケジュール ID）
     - `title`（名称）
     - `schedule_type`（この API では常に `"TODO"`）
     - `is_all_day`（日単位か否か）
     - 終日の場合: `start_date`, `end_date`
     - 分単位の場合: `start_datetime`, `end_datetime`
     - `is_todo_completed`（TODO の完了済みか否か）
     - `location`（場所）
     - `details`（詳細）
   - 並び順: `start_datetime` 昇順、`id` 昇順。

8. `GET /schedules/{schedule_id}`
   - ID で 1 件取得。
   - (6) の項目に加え `location`, `details` を含む。

9. `POST /schedules`
   - リクエストボディ例:
     ```json
     {
       "title": "資料作成",
       "start_datetime": "2026-03-20T09:00:00",
       "duration": 120,
       "is_all_day": false,
       "activity_category_id": 1,
       "schedule_type": "TODO",
       "location": "オフィス",
       "details": "明日の会議用",
       "is_todo_completed": false
     }
     ```

10. `PUT /schedules/{schedule_id}`
    - リクエストボディは `POST /schedules` と同じスキーマ。

11. `DELETE /schedules/{schedule_id}`
    - 論理削除（`is_deleted = true`）。

**ルーティング注意:** `GET /schedules/todo-alerts` は `GET /schedules/{schedule_id}` より具体的なパスのため、フレームワーク上は `/schedules/todo-alerts` が先に定義されている必要がある（本実装でその順序になっている）。

## 5. エラー応答

- `404`: リソースが見つからない。
- `409`: 祝日の日付の重複。
- `422`: バリデーションエラー（期間不正、終日の開始時刻不正、秒が 0 でないなど）。

## 6. 実装ファイル

- FastAPI エントリ: `app/main.py`
- SQLAlchemy モデル: `app/models.py`
- Pydantic スキーマ: `app/schemas.py`
- DB / セッション: `app/config.py`, `app/db.py`
