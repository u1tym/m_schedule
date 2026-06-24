# SCHEDULE (Vue 3 + TypeScript + Vite)

モバイル向けスケジュール画面のフロントエンドです。  
Vue 3 + TypeScript + Vite で構成されています。

## セットアップ

```bash
npm install
npm run dev
```

## API設定はどこで行うか

接続先は `src/config.ts` で管理しています。

### スケジュール API（予定・TODO）

- `apiOrigin` / `VITE_SCHEDULE_API_ORIGIN`: 本番のオリジン
- `apiDevPrefix`: 開発時プレフィックス（既定 `/api`）

- **開発時**  
  `getApiBaseUrl()` → `/api`。`vite.config.ts` の `server.proxy` が `http://127.0.0.1:8000` に転送します。
- **本番**  
  `getApiBaseUrl()` → `VITE_SCHEDULE_API_ORIGIN`（未設定時は `DEFAULT_API_ORIGIN`）。

### 設定 API（月表示・週始まり）

- `GET /settings` / `PUT /settings`（仕様はリポジトリ直下の **`API_CONFIG.md`** を参照）
- 本番の基点: **`VITE_CONFIG_API_ORIGIN`**（未設定時は `DEFAULT_CONFIG_API_ORIGIN` = `http://127.0.0.1:8000`）
- **開発時**は `getConfigApiBaseUrl()` も **`/api`** を返します（同一バックエンド上の `/settings` をプロキシ経由で呼ぶ想定）。

月表示の一覧／カレンダー・週の始まりは **Cookie ではなく** 起動時に `GET /settings` で取得し、歯車から変更したときに `PUT /settings` で保存します（キー名は API 仕様どおり `calender-monthly-type` / `calender-weekly-start`）。

### 認証 API（JWT 更新）

スケジュール API・設定 API の各リクエストの直前に **`POST /refresh`** を呼び出し、HttpOnly Cookie の JWT を延長します（仕様はリポジトリ直下の **`API_LOGIN_SPEC.md`** §4.3）。

- 基点: **`VITE_LOGIN_API_BASE_URL`**（未設定時は `http://127.0.0.1:8000/api/auth`）
- 例（Nginx）: `https://example.com/api/auth` → `/refresh` は `https://example.com/api/auth/refresh`

### 接続先を変えるには

1. 本番のスケジュール API: `VITE_SCHEDULE_API_ORIGIN` または `src/config.ts` の `DEFAULT_API_ORIGIN`
2. 本番の設定 API: **`VITE_CONFIG_API_ORIGIN`** または `DEFAULT_CONFIG_API_ORIGIN`
3. 認証 API（`/refresh`）: **`VITE_LOGIN_API_BASE_URL`**
4. 開発時のプロキシ先: `vite.config.ts` の `server.proxy['/api'].target`

## 注意喚起 TODO（初回表示）

初回の月データ読み込み後、**当日**を `ref_date` にして `GET /schedules/todo-alerts?ref_date=YYYY-MM-DD` を呼び出します。

- 1件以上ある場合のみモーダルで一覧表示します（完了済みは取り消し線）。
- 未完了はチェックで選択し、**「更新」** クリック時に `GET /schedules/{id}` → `PUT /schedules/{id}`（`is_todo_completed: true`）で完了更新します。
- API エラー時は画面全体を止めず、ポップアップは出しません（バックエンド未対応時のフォールバック）。

詳細はリポジトリ直下の `AI_SPECIFICATION.md` の **7. GET /schedules/todo-alerts** を参照してください。

## 主要コマンド

```bash
npm run dev     # 開発サーバ起動
npm run build   # 本番ビルド
npm run preview # ビルド結果をローカル確認
```
