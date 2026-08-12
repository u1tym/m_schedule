import { refreshAccessToken } from './auth'
import { getApiBaseUrl } from './config'
import type {
  ActivityCategory,
  Holiday,
  ScheduleDetail,
  ScheduleListItem,
  SchedulePayload,
  TodoAlertItem,
} from './types'

const apiBase = getApiBaseUrl()

const toQueryString = (params: Record<string, string | number | undefined>): string => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  })
  return query.toString()
}

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  await refreshAccessToken()
  const response = await fetch(`${apiBase}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const data = (await response.json()) as { detail?: string }
      if (data.detail) {
        message = data.detail
      }
    } catch (_error) {
      // Keep default error message when JSON parse fails.
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  getActivityCategories(includeDeleted = false): Promise<ActivityCategory[]> {
    const query = includeDeleted ? '?include_deleted=true' : ''
    return request<ActivityCategory[]>(`/activity-categories${query}`)
  },

  createActivityCategory(payload: { name: string; bg_color: string }): Promise<ActivityCategory> {
    return request<ActivityCategory>('/activity-categories', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateActivityCategory(
    id: number,
    payload: { name: string; bg_color: string; is_deleted: boolean },
  ): Promise<ActivityCategory> {
    return request<ActivityCategory>(`/activity-categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteActivityCategory(id: number): Promise<void> {
    return request<void>(`/activity-categories/${id}`, {
      method: 'DELETE',
    })
  },

  getHolidays(fromDate: string, toDate: string): Promise<Holiday[]> {
    const query = toQueryString({ from_date: fromDate, to_date: toDate })
    return request<Holiday[]>(`/holidays?${query}`)
  },

  getSchedules(fromDate: string, toDate: string): Promise<ScheduleListItem[]> {
    const query = toQueryString({ from_date: fromDate, to_date: toDate })
    return request<ScheduleListItem[]>(`/schedules?${query}`)
  },

  getTodoAlerts(refDate: string): Promise<TodoAlertItem[]> {
    const query = toQueryString({ ref_date: refDate })
    return request<TodoAlertItem[]>(`/schedules/todo-alerts?${query}`)
  },

  getSchedule(id: number): Promise<ScheduleDetail> {
    return request<ScheduleDetail>(`/schedules/${id}`)
  },

  createSchedule(payload: SchedulePayload): Promise<void> {
    return request<void>('/schedules', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateSchedule(id: number, payload: SchedulePayload): Promise<void> {
    return request<void>(`/schedules/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteSchedule(id: number): Promise<void> {
    return request<void>(`/schedules/${id}`, {
      method: 'DELETE',
    })
  },
}
