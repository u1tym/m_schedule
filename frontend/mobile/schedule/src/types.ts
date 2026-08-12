export type ScheduleType = '予定' | 'TODO'

export interface ActivityCategory {
  id: number
  name: string
  bg_color: string
  is_deleted: boolean
}


export interface Holiday {
  id: number
  date: string
  name: string
}

export interface ScheduleListItem {
  id: number
  title: string
  activity_category_id: number
  activity_category_name: string
  is_all_day: boolean
  start_date?: string
  end_date?: string
  start_datetime?: string
  end_datetime?: string
  schedule_type: ScheduleType
  is_todo_completed?: boolean
}

export interface SchedulePayload {
  title: string
  start_datetime: string
  duration: number
  is_all_day: boolean
  activity_category_id: number
  schedule_type: ScheduleType
  location: string
  details: string
  is_todo_completed: boolean
}

export interface ScheduleDetail extends ScheduleListItem {
  duration?: number
  location?: string
  details?: string
}

/** GET /schedules/todo-alerts の1件（仕様に沿った最小項目＋APIが返す追加項目用の任意項目） */
export interface TodoAlertItem {
  id: number
  title: string
  schedule_type: 'TODO'
  is_all_day: boolean
  start_date?: string
  end_date?: string
  start_datetime?: string
  end_datetime?: string
  is_todo_completed?: boolean
  location?: string
  details?: string
  activity_category_id?: number
  activity_category_name?: string
}
