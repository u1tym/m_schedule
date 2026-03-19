# m_schedule DB Layout and API Specification

## 1. Environment Variables

The API reads DB connection settings from `.env`.

```env
DB_SERVER=localhost
DB_PORT=5432
DB_NAME=tamtdb
DB_USERNAME=tamtuser
DB_PASSWORD=TAMTTAMT
```

Connection string pattern:

`postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}`

## 2. Database Layout

### 2.1 `activity_categories`

- Purpose: stores schedule category master data.
- Columns:
  - `id`: integer, PK
  - `name`: varchar, not null
  - `is_deleted`: boolean, not null (soft-delete flag)
  - `created_at`: timestamp, not null, default `now()`
  - `updated_at`: timestamp, not null, default `now()`

### 2.2 `holidays`

- Purpose: stores non-weekend holidays and holiday names.
- Columns:
  - `id`: integer, PK
  - `date`: date, not null, unique
  - `name`: varchar, not null
  - `created_at`: timestamp, nullable
  - `updated_at`: timestamp, nullable

### 2.3 `schedules`

- Purpose: stores schedules and TODO items.
- Columns:
  - `id`: integer, PK
  - `title`: varchar, not null
  - `start_datetime`: timestamp, not null
  - `duration`: integer, not null
  - `is_all_day`: boolean, not null
  - `activity_category_id`: integer, FK -> `activity_categories.id`
  - `schedule_type`: varchar, not null (`"予定"` or `"TODO"`)
  - `location`: varchar, nullable
  - `details`: text, nullable
  - `is_todo_completed`: boolean, not null
  - `is_deleted`: boolean, not null (soft-delete flag)
  - `created_at`: timestamp, not null, default `now()`
  - `updated_at`: timestamp, not null, default `now()`

## 3. Business Rules

### 3.1 All-day schedule

- `is_all_day = true`
- `start_datetime` must be `00:00:00`
- `duration` means days
- End date = start date + (`duration` - 1) days

### 3.2 Minute-based schedule

- `is_all_day = false`
- `start_datetime` includes date and time, and seconds must be `00`
- `duration` means minutes
- End datetime = start datetime + `duration` minutes

### 3.3 TODO behavior

- `schedule_type` is `"予定"` or `"TODO"`
- `is_todo_completed` is meaningful for `"TODO"`

## 4. API Endpoints

Base URL example: `http://localhost:8000`

### 4.1 Activity Categories

1. `GET /activity-categories`
   - Returns non-deleted categories.

2. `POST /activity-categories`
   - Body:
     ```json
     {
       "name": "会議"
     }
     ```

3. `DELETE /activity-categories/{category_id}`
   - Soft-delete (`is_deleted = true`).

### 4.2 Holidays

4. `GET /holidays?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
   - Both query params are optional.
   - If omitted, returns all holidays.
   - If specified, returns holidays in inclusive range.

5. `POST /holidays`
   - Body:
     ```json
     {
       "date": "2026-01-01",
       "name": "元日"
     }
     ```

### 4.3 Schedules

6. `GET /schedules?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
   - Required: `from_date`, `to_date`
   - Returns schedules overlapping:
     - from_date `00:00` to to_date `23:59` (inclusive)
   - Response item includes:
     - `id`
     - `title`
     - `activity_category_id`
     - `activity_category_name`
     - `is_all_day`
     - all-day: `start_date`, `end_date`
     - minute-based: `start_datetime`, `end_datetime`
     - `schedule_type` (`"予定"` or `"TODO"`)
     - for TODO: `is_todo_completed`

7. `GET /schedules/{schedule_id}`
   - Returns one schedule by ID.
   - Includes fields from (6) plus:
     - `location`
     - `details`

8. `POST /schedules`
   - Body example:
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

9. `PUT /schedules/{schedule_id}`
   - Same body schema as `POST /schedules`.

10. `DELETE /schedules/{schedule_id}`
    - Soft-delete (`is_deleted = true`).

## 5. Error Handling

- `404`: resource not found.
- `409`: duplicate holiday date.
- `422`: validation error (invalid period, invalid datetime for all-day, seconds not zero, etc.).

## 6. Implementation Files

- FastAPI app entrypoint: `app/main.py`
- SQLAlchemy models: `app/models.py`
- Pydantic schemas: `app/schemas.py`
- DB/session settings: `app/config.py`, `app/db.py`
