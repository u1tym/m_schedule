import { refreshAccessToken } from './auth'
import { getConfigApiBaseUrl } from './config'

/** 画面側の月表示モード（API の calender-monthly-type と対応） */
export type MonthDisplayMode = 'list' | 'calendar'

/** 週の始まり（API の calender-weekly-start と対応） */
export type WeekStartMode = 'sunday' | 'monday'

/** API・DB 仕様どおりの綴り */
export const SETTING_KEY_MONTHLY_TYPE = 'calender-monthly-type'
export const SETTING_KEY_WEEKLY_START = 'calender-weekly-start'

export type RawAppSettings = Record<string, string>

const joinUrl = (base: string, path: string): string => {
  const trimmed = base.replace(/\/$/, '')
  return `${trimmed}${path.startsWith('/') ? path : `/${path}`}`
}

const readErrorMessage = async (response: Response): Promise<string> => {
  let message = `HTTP ${response.status}`
  try {
    const data = (await response.json()) as { detail?: string; message?: string }
    if (data.detail) message = data.detail
    else if (data.message) message = data.message
  } catch {
    // ignore
  }
  return message
}

/** GET /settings — id=0 のキー・値マップ */
export const fetchAppSettings = async (): Promise<RawAppSettings> => {
  await refreshAccessToken()
  const base = getConfigApiBaseUrl()
  const response = await fetch(joinUrl(base, '/settings'), {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return (await response.json()) as RawAppSettings
}

/** PUT /settings — 本文は { id: 0, ...キー: 値 } */
export const putAppSettings = async (updates: Record<string, string>): Promise<void> => {
  await refreshAccessToken()
  const base = getConfigApiBaseUrl()
  const response = await fetch(joinUrl(base, '/settings'), {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: 0, ...updates }),
  })
  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
}

/** box → カレンダー, list → 一覧（未設定・その他は list） */
export const mapMonthlyTypeToDisplay = (raw: RawAppSettings): MonthDisplayMode => {
  const v = raw[SETTING_KEY_MONTHLY_TYPE]?.trim().toLowerCase()
  return v === 'box' ? 'calendar' : 'list'
}

export const mapWeeklyStartToDisplay = (raw: RawAppSettings): WeekStartMode => {
  const v = raw[SETTING_KEY_WEEKLY_START]?.trim().toLowerCase()
  return v === 'monday' ? 'monday' : 'sunday'
}

export const displayModeToMonthlyType = (mode: MonthDisplayMode): string =>
  mode === 'calendar' ? 'box' : 'list'

export const weekStartModeToWeeklyStart = (mode: WeekStartMode): string =>
  mode === 'monday' ? 'monday' : 'sunday'
