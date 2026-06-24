const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8000'
const DEFAULT_CONFIG_API_ORIGIN = 'http://127.0.0.1:8000'
/** 認証 API（POST /refresh）。Nginx 経由の例: http://host/api/auth */
const DEFAULT_LOGIN_API_BASE_URL = 'http://127.0.0.1:8000/api/auth'

export const appConfig = {
  apiOrigin: import.meta.env.VITE_SCHEDULE_API_ORIGIN || DEFAULT_API_ORIGIN,
  apiDevPrefix: '/api',
  /** 本番: 設定 API のオリジン（GET/PUT /settings） */
  configApiOrigin: import.meta.env.VITE_CONFIG_API_ORIGIN || DEFAULT_CONFIG_API_ORIGIN,
} as const

const trimTrailingSlash = (url: string): string => url.trim().replace(/\/$/, '')

/** 認証 API の基点（POST /refresh）。仕様は API_LOGIN_SPEC.md §4.3 */
export const getLoginApiBaseUrl = (): string => {
  const fromEnv = import.meta.env.VITE_LOGIN_API_BASE_URL
  if (typeof fromEnv === 'string' && fromEnv.trim() !== '') {
    return trimTrailingSlash(fromEnv)
  }
  return DEFAULT_LOGIN_API_BASE_URL
}

/** スケジュール API（既存） */
export const getApiBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return appConfig.apiDevPrefix
  }
  return appConfig.apiOrigin
}

/**
 * 設定 API（GET/PUT /settings）
 * 開発時はスケジュールと同一プロキシ `/api` 経由で同一ホストの `/settings` を呼ぶ想定。
 */
export const getConfigApiBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return appConfig.apiDevPrefix
  }
  return appConfig.configApiOrigin.replace(/\/$/, '')
}
