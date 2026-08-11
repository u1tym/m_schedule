<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { api } from './api'
import {
  displayModeToMonthlyType,
  fetchAppSettings,
  isCalendarDisplayMode,
  mapMonthlyTypeToDisplay,
  mapWeeklyStartToDisplay,
  type MonthDisplayMode,
  type MonthDisplaySelectable,
  putAppSettings,
  type RawAppSettings,
  SETTING_KEY_MONTHLY_TYPE,
  SETTING_KEY_WEEKLY_START,
  type WeekStartMode,
  weekStartModeToWeeklyStart,
} from './appSettings'
import type {
  ScheduleDetail,
  ScheduleListItem,
  SchedulePayload,
  ScheduleType,
  TodoAlertItem,
} from './types'
import scheduleIcon from '../images/SCHEDULE.png'
import portalIcon from '../images/PORTAL.png'
import configIcon from '../images/CONFIG.png'

interface DayRow {
  date: Date
  dateKey: string
  day: number
  weekdayLabel: string
  schedules: ScheduleListItem[]
  holidayName: string
  isHoliday: boolean
  isSaturday: boolean
  isSunday: boolean
  isToday: boolean
}

type DialogMode = 'create' | 'edit'

type ViewMode = 'month' | 'day'

interface TimedLayout {
  item: ScheduleListItem
  topPct: number
  heightPct: number
  lane: number
  laneCount: number
}

interface CalendarCell {
  key: string
  dateKey: string | null
  day: number | null
  inMonth: boolean
  hasSchedule: boolean
  categoryDotColors: string[]
  isToday: boolean
  isHoliday: boolean
  holidayName: string
  weekday: number
}

interface FormState {
  title: string
  scheduleType: ScheduleType
  categoryId: string
  isAllDay: boolean
  startDate: string
  endDate: string
  startTime: string
  endTime: string
  isTodoCompleted: boolean
  location: string
  details: string
}

const today = new Date()
const currentMonth = ref(new Date(today.getFullYear(), today.getMonth(), 1))
const categories = ref<{ id: number; name: string }[]>([])
const holidays = ref<Record<string, string>>({})
const schedules = ref<ScheduleListItem[]>([])

const isLoading = ref(false)
const errorMessage = ref('')

const viewMode = ref<ViewMode>('month')
const selectedDayKey = ref('')
const calendarSelectedDayKey = ref('')
const dayViewHolidayName = ref('')

const dayListEl = ref<HTMLElement | null>(null)
const hourTicks = Array.from({ length: 24 }, (_, index) => index)

const monthDisplayMode = ref<MonthDisplayMode>('list')
const weekStartsOn = ref<WeekStartMode>('sunday')
const rawAppSettings = ref<RawAppSettings>({})
const showMonthSettings = ref(false)
const monthSettingsError = ref('')
const monthSettingsSaving = ref(false)

const showDialog = ref(false)
const dialogMode = ref<DialogMode>('create')
const editingId = ref<number | null>(null)
const formError = ref('')
const selectedDateForCreate = ref('')

const todoAlerts = ref<TodoAlertItem[]>([])
const showTodoAlertPopup = ref(false)
const todoAlertSelectedIds = ref<number[]>([])
const todoAlertUpdatingBulk = ref(false)
const todoAlertError = ref('')

const form = reactive<FormState>({
  title: '',
  scheduleType: '予定',
  categoryId: '',
  isAllDay: false,
  startDate: '',
  endDate: '',
  startTime: '09:00',
  endTime: '10:00',
  isTodoCompleted: false,
  location: '',
  details: '',
})

const weekdays = ['日', '月', '火', '水', '木', '金', '土']
const categoryColors = ['#e0f2fe', '#dcfce7', '#fef3c7', '#fce7f3', '#ede9fe', '#ffedd5', '#ccfbf1']
const categoryDotColors = ['#0284c7', '#16a34a', '#d97706', '#db2777', '#7c3aed', '#ea580c', '#0f766e']

const monthLabel = computed(() => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth() + 1
  return `${year}年${String(month).padStart(2, '0')}月`
})

const monthRange = computed(() => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth()
  const start = new Date(year, month, 1)
  const end = new Date(year, month + 1, 0)
  return { start, end }
})

const dayRows = computed<DayRow[]>(() => {
  const rows: DayRow[] = []
  const { start, end } = monthRange.value
  const dayCount = end.getDate()
  const todayKey = toDateKey(new Date())
  for (let day = 1; day <= dayCount; day += 1) {
    const date = new Date(start.getFullYear(), start.getMonth(), day)
    const dateKey = toDateKey(date)
    const weekday = date.getDay()
    const holidayName = holidays.value[dateKey] || ''
    rows.push({
      date,
      dateKey,
      day,
      weekdayLabel: weekdays[weekday],
      schedules: schedulesForDay(dateKey),
      holidayName,
      isHoliday: Boolean(holidayName),
      isSaturday: weekday === 6,
      isSunday: weekday === 0,
      isToday: dateKey === todayKey,
    })
  }
  return rows
})

const categoryColorMap = computed(() => {
  const map = new Map<number, string>()
  categories.value.forEach((category, index) => {
    map.set(category.id, categoryColors[index % categoryColors.length])
  })
  return map
})

const categoryDotColorMap = computed(() => {
  const map = new Map<number, string>()
  categories.value.forEach((category, index) => {
    map.set(category.id, categoryDotColors[index % categoryDotColors.length])
  })
  return map
})

const toDateKey = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const toDateTimeString = (date: string, time = '00:00'): string => `${date}T${time}:00`

const parseDate = (value: string): Date => new Date(`${value}T00:00:00`)

const formatClock = (iso: string): string => {
  const date = new Date(iso)
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

const schedulesForDay = (dateKey: string): ScheduleListItem[] => {
  return schedules.value.filter((item) => {
    if (item.is_all_day && item.start_date && item.end_date) {
      return dateKey >= item.start_date && dateKey <= item.end_date
    }
    if (!item.is_all_day && item.start_datetime) {
      return item.start_datetime.slice(0, 10) === dateKey
    }
    return false
  })
}

const calendarWeekdayHeaders = computed((): string[] => {
  if (weekStartsOn.value === 'sunday') {
    return weekdays
  }
  return [...weekdays.slice(1), weekdays[0]!]
})

const calendarCells = computed((): CalendarCell[] => {
  const { start, end } = monthRange.value
  const year = start.getFullYear()
  const month = start.getMonth()
  const daysInMonth = end.getDate()
  const firstWeekday = new Date(year, month, 1).getDay()
  const leadingEmpty =
    weekStartsOn.value === 'sunday' ? firstWeekday : (firstWeekday + 6) % 7
  const todayKey = toDateKey(new Date())
  const cells: CalendarCell[] = []
  const totalSlots = 42

  for (let index = 0; index < totalSlots; index += 1) {
    const dayNum = index - leadingEmpty + 1
    if (dayNum < 1 || dayNum > daysInMonth) {
      cells.push({
        key: `pad-${index}`,
        dateKey: null,
        day: null,
        inMonth: false,
        hasSchedule: false,
        categoryDotColors: [],
        isToday: false,
        isHoliday: false,
        holidayName: '',
        weekday: -1,
      })
      continue
    }
    const date = new Date(year, month, dayNum)
    const dateKey = toDateKey(date)
    const weekday = date.getDay()
    const holidayName = holidays.value[dateKey] || ''
    const categoryDotColors = calendarDotColorsForDay(dateKey)
    cells.push({
      key: dateKey,
      dateKey,
      day: dayNum,
      inMonth: true,
      hasSchedule: categoryDotColors.length > 0,
      categoryDotColors,
      isToday: dateKey === todayKey,
      isHoliday: Boolean(holidayName),
      holidayName,
      weekday,
    })
  }
  return cells
})

const scheduleText = (item: ScheduleListItem): string => {
  if (item.is_all_day) {
    return item.title
  }
  if (!item.start_datetime || !item.end_datetime) {
    return item.title
  }
  return `${formatClock(item.start_datetime)}～${formatClock(item.end_datetime)} ${item.title}`
}

const scheduleClass = (row: DayRow): string => {
  if (row.isHoliday || row.isSunday) {
    return 'date-sun-holiday'
  }
  if (row.isSaturday) {
    return 'date-saturday'
  }
  return 'date-weekday'
}

const rowClass = (row: DayRow): string => {
  if (row.isHoliday || row.isSunday) {
    return 'row-sun-holiday'
  }
  if (row.isSaturday) {
    return 'row-saturday'
  }
  return 'row-weekday'
}

const backgroundColor = (item: ScheduleListItem): string => {
  return categoryColorMap.value.get(item.activity_category_id) || '#f3f4f6'
}

const calendarDotColorsForDay = (dateKey: string): string[] => {
  const colors = new Set<string>()
  schedulesForDay(dateKey).forEach((item) => {
    colors.add(categoryDotColorMap.value.get(item.activity_category_id) || '#2563eb')
  })
  return Array.from(colors)
}

const pad2 = (value: number): string => String(value).padStart(2, '0')

const dayViewDateLabel = computed(() => {
  if (!selectedDayKey.value) return ''
  const date = parseDate(selectedDayKey.value)
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
})

const dayViewWeekdayLabel = computed(() => {
  if (!selectedDayKey.value) return ''
  return weekdays[parseDate(selectedDayKey.value).getDay()]
})

const dayViewIsToday = computed(
  () => selectedDayKey.value !== '' && selectedDayKey.value === toDateKey(new Date()),
)

const dayViewWeekdayIndex = computed(() => {
  if (!selectedDayKey.value) return -1
  return parseDate(selectedDayKey.value).getDay()
})

const calendarSelectedDateLabel = computed(() => {
  if (!calendarSelectedDayKey.value) return ''
  const date = parseDate(calendarSelectedDayKey.value)
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
})

const calendarSelectedWeekdayLabel = computed(() => {
  if (!calendarSelectedDayKey.value) return ''
  return weekdays[parseDate(calendarSelectedDayKey.value).getDay()]
})

const calendarSelectedHolidayName = computed(() => {
  if (!calendarSelectedDayKey.value) return ''
  return holidays.value[calendarSelectedDayKey.value] || ''
})

const calendarSelectedSchedules = computed((): ScheduleListItem[] => {
  if (!calendarSelectedDayKey.value) return []
  return schedulesForDay(calendarSelectedDayKey.value)
})

const dayViewAllDaySchedules = computed((): ScheduleListItem[] => {
  if (viewMode.value !== 'day' || !selectedDayKey.value) return []
  const key = selectedDayKey.value
  return schedules.value.filter((item) => {
    if (!item.is_all_day || !item.start_date || !item.end_date) return false
    return key >= item.start_date && key <= item.end_date
  })
})

const dayViewTimedSchedules = computed((): ScheduleListItem[] => {
  if (viewMode.value !== 'day' || !selectedDayKey.value) return []
  const key = selectedDayKey.value
  return schedules.value.filter(
    (item) =>
      !item.is_all_day &&
      item.start_datetime &&
      item.end_datetime &&
      item.start_datetime.slice(0, 10) === key,
  )
})

const timedLayouts = computed((): TimedLayout[] => {
  const items = dayViewTimedSchedules.value
  const enriched = items
    .map((item) => {
      const start = new Date(item.start_datetime!)
      const end = new Date(item.end_datetime!)
      const startMin = start.getHours() * 60 + start.getMinutes() + start.getSeconds() / 60
      let endMin = end.getHours() * 60 + end.getMinutes() + end.getSeconds() / 60
      if (!Number.isFinite(startMin) || !Number.isFinite(endMin) || endMin <= startMin) {
        endMin = startMin + 30
      }
      const dayMinutes = 24 * 60
      const clampedStart = Math.max(0, Math.min(startMin, dayMinutes - 1))
      const clampedEnd = Math.max(clampedStart + 15, Math.min(endMin, dayMinutes))
      return { item, startMin: clampedStart, endMin: clampedEnd }
    })
    .sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin)

  const laneEnds: number[] = []
  const layouts: TimedLayout[] = []

  for (const row of enriched) {
    let lane = 0
    while (lane < laneEnds.length && laneEnds[lane]! > row.startMin) {
      lane += 1
    }
    if (lane === laneEnds.length) {
      laneEnds.push(row.endMin)
    } else {
      laneEnds[lane] = row.endMin
    }
    layouts.push({
      item: row.item,
      topPct: (row.startMin / 1440) * 100,
      heightPct: Math.max(((row.endMin - row.startMin) / 1440) * 100, 2),
      lane,
      laneCount: 1,
    })
  }

  const laneCount = Math.max(1, laneEnds.length)
  layouts.forEach((layout) => {
    layout.laneCount = laneCount
  })
  return layouts
})

const loadDayData = async (dayKey: string, options?: { silent?: boolean }): Promise<void> => {
  const silent = Boolean(options?.silent)
  if (!silent) {
    isLoading.value = true
    errorMessage.value = ''
    dayViewHolidayName.value = ''
  }
  try {
    const [holidayData, scheduleData] = await Promise.all([
      api.getHolidays(dayKey, dayKey),
      api.getSchedules(dayKey, dayKey),
    ])
    const holiday = holidayData.find((item) => item.date === dayKey)
    dayViewHolidayName.value = holiday?.name || ''
    schedules.value = scheduleData
  } catch (error) {
    if (!silent) {
      errorMessage.value = error instanceof Error ? error.message : 'データの取得に失敗しました。'
    }
  } finally {
    if (!silent) {
      isLoading.value = false
    }
  }
}

const openDayView = async (dateKey: string): Promise<void> => {
  showMonthSettings.value = false
  viewMode.value = 'day'
  selectedDayKey.value = dateKey
  const date = parseDate(dateKey)
  currentMonth.value = new Date(date.getFullYear(), date.getMonth(), 1)
  await loadDayData(dateKey)
}

const backToMonth = async (): Promise<void> => {
  viewMode.value = 'month'
  selectedDayKey.value = ''
  dayViewHolidayName.value = ''
  await loadMonthData()
  await nextTick()
  if (monthDisplayMode.value === 'list' && dayListEl.value) {
    dayListEl.value.scrollTop = 0
  }
}

const shiftDay = async (delta: number): Promise<void> => {
  if (!selectedDayKey.value) return
  const date = parseDate(selectedDayKey.value)
  date.setDate(date.getDate() + delta)
  const nextKey = toDateKey(date)
  selectedDayKey.value = nextKey
  currentMonth.value = new Date(date.getFullYear(), date.getMonth(), 1)
  await loadDayData(nextKey)
}

const onMonthScheduleColClick = (event: MouseEvent, dateKey: string): void => {
  if ((event.target as HTMLElement).closest('.schedule-chip')) return
  openCreateDialog(dateKey)
}

const onAllDayAreaClick = (event: MouseEvent): void => {
  if ((event.target as HTMLElement).closest('.day-view-all-day-block')) return
  if (!selectedDayKey.value) return
  openCreateDialog(selectedDayKey.value, { allDay: true })
}

const timeBlockStyle = (layout: TimedLayout): Record<string, string> => {
  const lanes = layout.laneCount
  const share = 100 / lanes
  return {
    top: `${layout.topPct}%`,
    height: `${layout.heightPct}%`,
    left: lanes > 1 ? `${share * layout.lane}%` : '4px',
    width: lanes > 1 ? `calc(${share}% - 6px)` : 'calc(100% - 8px)',
    backgroundColor: backgroundColor(layout.item),
  }
}

const onDayTimelineClick = (event: MouseEvent): void => {
  if (!selectedDayKey.value) return
  if ((event.target as HTMLElement).closest('.day-view-time-block')) return
  const element = event.currentTarget as HTMLElement
  const rect = element.getBoundingClientRect()
  const y = event.clientY - rect.top
  const ratio = Math.min(1, Math.max(0, y / rect.height))
  const totalMin = Math.floor((ratio * 1440) / 30) * 30
  const startH = Math.floor(totalMin / 60)
  const startM = totalMin % 60
  let endTotal = totalMin + 60
  if (endTotal > 1440) endTotal = 1440
  const endH = Math.floor(endTotal / 60)
  const endM = endTotal % 60
  openCreateDialog(selectedDayKey.value, {
    startTime: `${pad2(startH)}:${pad2(startM)}`,
    endTime: `${pad2(endH)}:${pad2(endM)}`,
  })
}

const toPayload = (): SchedulePayload => {
  if (!form.title.trim()) {
    throw new Error('タイトルを入力してください。')
  }
  if (!form.categoryId) {
    throw new Error('カテゴリを選択してください。')
  }

  if (form.isAllDay) {
    if (!form.startDate || !form.endDate) {
      throw new Error('開始日と終了日を入力してください。')
    }
    const start = parseDate(form.startDate)
    const end = parseDate(form.endDate)
    if (end < start) {
      throw new Error('終了日は開始日以降を指定してください。')
    }
    const days = Math.floor((end.getTime() - start.getTime()) / 86400000) + 1
    return {
      title: form.title.trim(),
      start_datetime: toDateTimeString(form.startDate),
      duration: days,
      is_all_day: true,
      activity_category_id: Number(form.categoryId),
      schedule_type: form.scheduleType,
      location: form.location.trim(),
      details: form.details.trim(),
      is_todo_completed: form.scheduleType === 'TODO' ? form.isTodoCompleted : false,
    }
  }

  if (!form.startDate || !form.startTime || !form.endTime) {
    throw new Error('日付と時間を入力してください。')
  }
  const startDateTime = new Date(toDateTimeString(form.startDate, form.startTime))
  const endDateTime = new Date(toDateTimeString(form.startDate, form.endTime))
  if (endDateTime <= startDateTime) {
    throw new Error('終了時刻は開始時刻より後にしてください。')
  }
  const minutes = Math.floor((endDateTime.getTime() - startDateTime.getTime()) / 60000)
  return {
    title: form.title.trim(),
    start_datetime: toDateTimeString(form.startDate, form.startTime),
    duration: minutes,
    is_all_day: false,
    activity_category_id: Number(form.categoryId),
    schedule_type: form.scheduleType,
    location: form.location.trim(),
    details: form.details.trim(),
    is_todo_completed: form.scheduleType === 'TODO' ? form.isTodoCompleted : false,
  }
}

const openCreateDialog = (
  dateKey: string,
  options?: { startTime?: string; endTime?: string; allDay?: boolean },
): void => {
  dialogMode.value = 'create'
  editingId.value = null
  formError.value = ''
  selectedDateForCreate.value = dateKey
  form.title = ''
  form.scheduleType = '予定'
  form.categoryId = categories.value[0] ? String(categories.value[0].id) : ''
  const allDay = Boolean(options?.allDay)
  form.isAllDay = allDay
  form.startDate = dateKey
  form.endDate = dateKey
  form.startTime = options?.startTime ?? '09:00'
  form.endTime = options?.endTime ?? '10:00'
  form.isTodoCompleted = false
  form.location = ''
  form.details = ''
  showDialog.value = true
}

const openEditDialog = async (item: ScheduleListItem): Promise<void> => {
  dialogMode.value = 'edit'
  editingId.value = item.id
  formError.value = ''
  form.title = item.title
  form.scheduleType = item.schedule_type
  form.categoryId = String(item.activity_category_id)
  form.isAllDay = item.is_all_day
  form.isTodoCompleted = Boolean(item.is_todo_completed)
  form.location = ''
  form.details = ''
  if (item.is_all_day && item.start_date && item.end_date) {
    form.startDate = item.start_date
    form.endDate = item.end_date
    form.startTime = '09:00'
    form.endTime = '10:00'
  } else if (item.start_datetime && item.end_datetime) {
    form.startDate = item.start_datetime.slice(0, 10)
    form.endDate = item.start_datetime.slice(0, 10)
    form.startTime = item.start_datetime.slice(11, 16)
    form.endTime = item.end_datetime.slice(11, 16)
  }
  try {
    const detail = await api.getSchedule(item.id)
    form.location = detail.location || ''
    form.details = detail.details || ''
  } catch (_error) {
    // Keep list data for editing even if detail fetch fails.
  }
  showDialog.value = true
}

const closeDialog = (): void => {
  showDialog.value = false
}

const saveSchedule = async (): Promise<void> => {
  formError.value = ''
  try {
    const payload = toPayload()
    if (dialogMode.value === 'create') {
      await api.createSchedule(payload)
    } else if (editingId.value !== null) {
      await api.updateSchedule(editingId.value, payload)
    }
    showDialog.value = false
    if (viewMode.value === 'day' && selectedDayKey.value) {
      await loadDayData(selectedDayKey.value)
    } else {
      await loadMonthData()
    }
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '保存に失敗しました。'
  }
}

const removeSchedule = async (): Promise<void> => {
  if (editingId.value === null) {
    return
  }
  const ok = window.confirm('この予定を削除しますか？')
  if (!ok) {
    return
  }
  try {
    await api.deleteSchedule(editingId.value)
    showDialog.value = false
    if (viewMode.value === 'day' && selectedDayKey.value) {
      await loadDayData(selectedDayKey.value)
    } else {
      await loadMonthData()
    }
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '削除に失敗しました。'
  }
}

const shiftMonth = async (delta: number): Promise<void> => {
  const date = currentMonth.value
  currentMonth.value = new Date(date.getFullYear(), date.getMonth() + delta, 1)
  calendarSelectedDayKey.value = ''
  await loadMonthData()
  await nextTick()
  if (monthDisplayMode.value === 'list' && dayListEl.value) {
    dayListEl.value.scrollTop = 0
  }
}

const onCalendarCellClick = (dateKey: string): void => {
  calendarSelectedDayKey.value = dateKey
}

const openPortal = (): void => {
  window.location.href = '/mobile/login/#/menu'
}

const toggleMonthSettings = (): void => {
  showMonthSettings.value = !showMonthSettings.value
  if (showMonthSettings.value) {
    monthSettingsError.value = ''
  }
}

const loadAppSettings = async (): Promise<void> => {
  try {
    const raw = await fetchAppSettings()
    rawAppSettings.value = { ...raw }
    monthDisplayMode.value = mapMonthlyTypeToDisplay(raw)
    weekStartsOn.value = mapWeeklyStartToDisplay(raw)
  } catch {
    rawAppSettings.value = {}
    monthDisplayMode.value = 'list'
    weekStartsOn.value = 'sunday'
  }
}

const setMonthDisplayMode = async (mode: MonthDisplaySelectable): Promise<void> => {
  const previous = monthDisplayMode.value
  monthSettingsError.value = ''
  monthDisplayMode.value = mode
  monthSettingsSaving.value = true
  try {
    const monthlyType = displayModeToMonthlyType(mode)
    await putAppSettings({ [SETTING_KEY_MONTHLY_TYPE]: monthlyType })
    rawAppSettings.value = {
      ...rawAppSettings.value,
      [SETTING_KEY_MONTHLY_TYPE]: monthlyType,
    }
    if (isCalendarDisplayMode(mode) && !calendarSelectedDayKey.value) {
      calendarSelectedDayKey.value = toDateKey(new Date())
    }
  } catch (error) {
    monthDisplayMode.value = previous
    monthSettingsError.value =
      error instanceof Error ? error.message : '設定の保存に失敗しました。'
  } finally {
    monthSettingsSaving.value = false
  }
}

const setWeekStartsOn = async (mode: WeekStartMode): Promise<void> => {
  const previous = weekStartsOn.value
  monthSettingsError.value = ''
  weekStartsOn.value = mode
  monthSettingsSaving.value = true
  try {
    await putAppSettings({ [SETTING_KEY_WEEKLY_START]: weekStartModeToWeeklyStart(mode) })
    rawAppSettings.value = {
      ...rawAppSettings.value,
      [SETTING_KEY_WEEKLY_START]: weekStartModeToWeeklyStart(mode),
    }
  } catch (error) {
    weekStartsOn.value = previous
    monthSettingsError.value =
      error instanceof Error ? error.message : '設定の保存に失敗しました。'
  } finally {
    monthSettingsSaving.value = false
  }
}

const loadMonthData = async (options?: { silent?: boolean }): Promise<void> => {
  const silent = Boolean(options?.silent)
  const fromDate = toDateKey(monthRange.value.start)
  const toDate = toDateKey(monthRange.value.end)
  if (!silent) {
    isLoading.value = true
    errorMessage.value = ''
  }
  try {
    const [categoryData, holidayData, scheduleData] = await Promise.all([
      api.getActivityCategories(),
      api.getHolidays(fromDate, toDate),
      api.getSchedules(fromDate, toDate),
    ])
    categories.value = categoryData
    holidays.value = holidayData.reduce<Record<string, string>>((acc, holiday) => {
      acc[holiday.date] = holiday.name
      return acc
    }, {})
    schedules.value = scheduleData
  } catch (error) {
    if (!silent) {
      errorMessage.value = error instanceof Error ? error.message : 'データの取得に失敗しました。'
    }
  } finally {
    if (!silent) {
      isLoading.value = false
    }
  }
}

const detailToPayloadForUpdate = (
  detail: ScheduleDetail,
  isTodoCompleted: boolean,
): SchedulePayload => {
  const location = (detail.location || '').trim()
  const details = (detail.details || '').trim()

  if (detail.is_all_day && detail.start_date && detail.end_date) {
    const start = parseDate(detail.start_date)
    const end = parseDate(detail.end_date)
    if (end < start) {
      throw new Error('終了日は開始日以降を指定してください。')
    }
    const dayCount = Math.floor((end.getTime() - start.getTime()) / 86400000) + 1
    return {
      title: detail.title.trim(),
      start_datetime: toDateTimeString(detail.start_date),
      duration: dayCount,
      is_all_day: true,
      activity_category_id: detail.activity_category_id,
      schedule_type: detail.schedule_type,
      location,
      details,
      is_todo_completed: detail.schedule_type === 'TODO' ? isTodoCompleted : false,
    }
  }

  if (!detail.start_datetime || !detail.end_datetime) {
    throw new Error('スケジュール形式が不正です。')
  }

  const startDateTime = new Date(detail.start_datetime)
  const endDateTime = new Date(detail.end_datetime)
  if (Number.isNaN(startDateTime.getTime()) || Number.isNaN(endDateTime.getTime())) {
    throw new Error('日時が不正です。')
  }
  if (endDateTime <= startDateTime) {
    throw new Error('終了時刻は開始時刻より後にしてください。')
  }
  const minutes = Math.max(
    1,
    Math.floor((endDateTime.getTime() - startDateTime.getTime()) / 60000),
  )
  const datePart = detail.start_datetime.slice(0, 10)
  const timePart = detail.start_datetime.slice(11, 16)
  return {
    title: detail.title.trim(),
    start_datetime: toDateTimeString(datePart, timePart),
    duration: minutes,
    is_all_day: false,
    activity_category_id: detail.activity_category_id,
    schedule_type: detail.schedule_type,
    location,
    details,
    is_todo_completed: detail.schedule_type === 'TODO' ? isTodoCompleted : false,
  }
}

const todoAlertWhenLabel = (item: TodoAlertItem): string => {
  if (item.is_all_day && item.start_date) {
    const tail = item.end_date && item.end_date !== item.start_date ? ` ～ ${item.end_date}` : ''
    return `終日 ${item.start_date}${tail}`
  }
  if (item.start_datetime && item.end_datetime) {
    return `${formatClock(item.start_datetime)}～${formatClock(item.end_datetime)}`
  }
  return ''
}

const onTodoAlertSelectionChange = (id: number, event: Event): void => {
  const checkbox = event.target as HTMLInputElement
  if (checkbox.checked) {
    if (!todoAlertSelectedIds.value.includes(id)) {
      todoAlertSelectedIds.value = [...todoAlertSelectedIds.value, id]
    }
  } else {
    todoAlertSelectedIds.value = todoAlertSelectedIds.value.filter((x) => x !== id)
  }
}

const applyTodoAlertUpdates = async (): Promise<void> => {
  const ids = [...todoAlertSelectedIds.value]
  if (ids.length === 0) {
    return
  }
  todoAlertError.value = ''
  todoAlertUpdatingBulk.value = true
  try {
    for (const id of ids) {
      const row = todoAlerts.value.find((item) => item.id === id)
      if (!row || row.is_todo_completed) {
        continue
      }
      const detail = await api.getSchedule(id)
      const payload = detailToPayloadForUpdate(detail, true)
      await api.updateSchedule(id, payload)
      row.is_todo_completed = true
    }
    todoAlertSelectedIds.value = []
    if (viewMode.value === 'day' && selectedDayKey.value) {
      await loadDayData(selectedDayKey.value, { silent: true })
    } else {
      await loadMonthData({ silent: true })
    }
  } catch (error) {
    todoAlertError.value =
      error instanceof Error ? error.message : '完了への更新に失敗しました。'
    todoAlertSelectedIds.value = todoAlertSelectedIds.value.filter((id) => {
      const row = todoAlerts.value.find((item) => item.id === id)
      return Boolean(row && !row.is_todo_completed)
    })
  } finally {
    todoAlertUpdatingBulk.value = false
  }
}

const closeTodoAlertPopup = (): void => {
  showTodoAlertPopup.value = false
  todoAlertSelectedIds.value = []
  todoAlertError.value = ''
}

const fetchTodoAlertsOnStartup = async (): Promise<void> => {
  try {
    const refDate = toDateKey(new Date())
    const items = await api.getTodoAlerts(refDate)
    if (items.length > 0) {
      todoAlerts.value = items
      todoAlertSelectedIds.value = []
      showTodoAlertPopup.value = true
    }
  } catch {
    // 初回表示を妨げない（API 未対応時などは無視）
  }
}

onMounted(async () => {
  await Promise.all([loadMonthData(), loadAppSettings()])
  if (viewMode.value === 'month' && isCalendarDisplayMode(monthDisplayMode.value)) {
    calendarSelectedDayKey.value = toDateKey(new Date())
  }
  await fetchTodoAlertsOnStartup()
})
</script>

<template>
  <main class="mobile-root">
    <header class="header">
      <div class="header-top">
        <div class="header-leading">
          <button
            class="header-round-btn header-round-btn--lg"
            type="button"
            aria-label="PORTALへ移動"
            @click="openPortal"
          >
            <img :src="portalIcon" alt="" class="header-icon-circle header-icon-circle--lg" />
          </button>
          <div class="header-icon-frame header-icon-frame--lg" aria-hidden="true">
            <img :src="scheduleIcon" alt="" class="header-icon-circle header-icon-circle--lg" />
          </div>
          <strong class="header-title">SCHEDULE</strong>
        </div>
        <button
          class="header-round-btn header-round-btn--sm"
          type="button"
          aria-label="月表示の設定"
          @click="toggleMonthSettings"
        >
          <img :src="configIcon" alt="" class="header-icon-circle header-icon-circle--sm" />
        </button>
      </div>
      <div v-if="viewMode === 'month'" class="month-nav">
        <button type="button" class="nav-button" @click="shiftMonth(-1)">＜</button>
        <strong>{{ monthLabel }}</strong>
        <button type="button" class="nav-button" @click="shiftMonth(1)">＞</button>
      </div>
      <div v-else class="day-nav">
        <button type="button" class="nav-button" aria-label="前日" @click="shiftDay(-1)">＜</button>
        <div
          class="day-nav-center"
          :class="{
            'day-nav-center--today': dayViewIsToday,
            'day-nav-center--sun': dayViewWeekdayIndex === 0,
            'day-nav-center--sat': dayViewWeekdayIndex === 6,
          }"
        >
          <div class="day-nav-date-line">
            <strong class="day-nav-date">{{ dayViewDateLabel }}</strong>
            <span class="day-nav-weekday">（{{ dayViewWeekdayLabel }}）</span>
          </div>
          <p v-if="dayViewHolidayName" class="day-nav-holiday">{{ dayViewHolidayName }}</p>
        </div>
        <button type="button" class="nav-button" aria-label="翌日" @click="shiftDay(1)">＞</button>
      </div>
      <button
        v-if="viewMode === 'day'"
        type="button"
        class="day-back-month"
        @click="backToMonth"
      >
        月表示に戻る
      </button>
    </header>

    <p v-if="errorMessage" class="message error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="message">読み込み中...</p>

    <section
      v-if="viewMode === 'month' && monthDisplayMode === 'list'"
      ref="dayListEl"
      class="day-list"
    >
      <article
        v-for="row in dayRows"
        :key="row.dateKey"
        class="day-row"
        :class="[rowClass(row), { 'day-row--today': row.isToday }]"
        :aria-current="row.isToday ? 'date' : undefined"
      >
        <div
          class="date-col"
          :class="[scheduleClass(row), { 'date-col--today': row.isToday }]"
          role="button"
          tabindex="0"
          @click.stop="openDayView(row.dateKey)"
          @keydown.enter.prevent="openDayView(row.dateKey)"
          @keydown.space.prevent="openDayView(row.dateKey)"
        >
          <span class="day-number">{{ row.day }}</span>
          <span class="weekday">({{ row.weekdayLabel }})</span>
        </div>
        <div
          class="schedule-col"
          :class="{ 'schedule-col--today': row.isToday }"
          @click="onMonthScheduleColClick($event, row.dateKey)"
        >
          <p v-if="row.holidayName" class="holiday-name">{{ row.holidayName }}</p>
          <div
            v-for="item in row.schedules"
            :key="item.id"
            class="schedule-chip"
            :style="{ backgroundColor: backgroundColor(item) }"
            @click.stop="openEditDialog(item)"
          >
            <template v-if="item.schedule_type === 'TODO'">
              <span class="todo-box">{{ item.is_todo_completed ? '☑' : '□' }}</span>
              <span :class="{ completed: item.is_todo_completed }">{{ scheduleText(item) }}</span>
            </template>
            <template v-else>
              <span>{{ scheduleText(item) }}</span>
            </template>
          </div>
        </div>
      </article>
    </section>

    <section
      v-else-if="viewMode === 'month' && isCalendarDisplayMode(monthDisplayMode)"
      class="month-calendar"
      aria-label="月カレンダー"
    >
      <div class="month-cal-weekdays" role="row">
        <div
          v-for="(label, index) in calendarWeekdayHeaders"
          :key="'wd-' + index"
          class="month-cal-weekday"
          :class="{
            'month-cal-weekday--sun': weekStartsOn === 'sunday' ? index === 0 : index === 6,
            'month-cal-weekday--sat': weekStartsOn === 'sunday' ? index === 6 : index === 5,
          }"
          role="columnheader"
        >
          {{ label }}
        </div>
      </div>
      <div class="month-cal-grid" role="grid">
        <template v-for="cell in calendarCells" :key="cell.key">
          <button
            v-if="cell.inMonth && cell.dateKey"
            type="button"
            class="month-cal-cell"
            :class="{
              'month-cal-cell--today': cell.isToday,
              'month-cal-cell--selected': calendarSelectedDayKey === cell.dateKey,
              'month-cal-cell--sun': cell.weekday === 0 && !cell.isHoliday,
              'month-cal-cell--sat': cell.weekday === 6,
              'month-cal-cell--holiday': cell.isHoliday,
            }"
            :aria-label="
              cell.hasSchedule ? `${cell.day}日、予定あり` : `${cell.day}日、予定なし`
            "
            @click="onCalendarCellClick(cell.dateKey)"
          >
            <span class="month-cal-day">{{ cell.day }}</span>
            <span class="month-cal-dots" aria-hidden="true">
              <span
                v-for="(dotColor, dotIndex) in cell.categoryDotColors"
                :key="`${cell.key}-dot-${dotIndex}`"
                class="month-cal-dot"
                :style="{ backgroundColor: dotColor }"
              />
            </span>
          </button>
          <div v-else class="month-cal-cell month-cal-cell--pad" aria-hidden="true" />
        </template>
      </div>
      <section v-if="calendarSelectedDayKey" class="month-cal-detail">
        <button
          type="button"
          class="month-cal-detail-head"
          @click="openDayView(calendarSelectedDayKey)"
        >
          <h3 class="month-cal-detail-title">
            {{ calendarSelectedDateLabel }}（{{ calendarSelectedWeekdayLabel }}）
          </h3>
          <p v-if="calendarSelectedHolidayName" class="month-cal-detail-holiday">
            {{ calendarSelectedHolidayName }}
          </p>
        </button>
        <div v-if="calendarSelectedSchedules.length === 0" class="month-cal-detail-empty">
          予定・TODOはありません
        </div>
        <div
          v-for="item in calendarSelectedSchedules"
          :key="`calendar-detail-${item.id}`"
          class="month-cal-detail-item schedule-chip"
          :style="{ backgroundColor: backgroundColor(item) }"
          @click.stop="openEditDialog(item)"
        >
          <template v-if="item.schedule_type === 'TODO'">
            <span class="todo-box">{{ item.is_todo_completed ? '☑' : '□' }}</span>
            <span :class="{ completed: item.is_todo_completed }">{{ scheduleText(item) }}</span>
          </template>
          <template v-else>
            <span>{{ scheduleText(item) }}</span>
          </template>
        </div>
      </section>
    </section>

    <p
      v-else-if="viewMode === 'month' && monthDisplayMode === 'none'"
      class="message month-display-none"
    >
      カレンダーなし
    </p>

    <button
      v-if="viewMode === 'month' && isCalendarDisplayMode(monthDisplayMode) && calendarSelectedDayKey"
      type="button"
      class="month-cal-fab"
      aria-label="新規スケジュール"
      @click="openCreateDialog(calendarSelectedDayKey)"
    >
      <span class="month-cal-fab-icon" aria-hidden="true">+</span>
    </button>

    <section v-if="viewMode === 'day'" class="day-view">
      <div class="day-view-all-day">
        <div class="day-view-gutter day-view-gutter--all-day">全日</div>
        <div class="day-view-all-day-body" @click="onAllDayAreaClick">
          <div
            v-for="item in dayViewAllDaySchedules"
            :key="item.id"
            class="day-view-all-day-block"
            :style="{ backgroundColor: backgroundColor(item) }"
            @click.stop="openEditDialog(item)"
          >
            <template v-if="item.schedule_type === 'TODO'">
              <span class="todo-box">{{ item.is_todo_completed ? '☑' : '□' }}</span>
              <span :class="{ completed: item.is_todo_completed }">{{ item.title }}</span>
            </template>
            <template v-else>
              <span>{{ item.title }}</span>
            </template>
          </div>
        </div>
      </div>
      <div class="day-view-timeline">
        <div class="day-view-hours">
          <div
            v-for="hour in hourTicks"
            :key="hour"
            class="day-view-hour-label"
          >
            {{ hour }}:00
          </div>
          <span class="day-view-hour-end" aria-hidden="true">24:00</span>
        </div>
        <div class="day-view-track-wrap">
          <div class="day-view-track" @click="onDayTimelineClick">
            <div
              v-for="hour in hourTicks"
              :key="'line-' + hour"
              class="day-view-hour-row"
            />
            <div
              v-for="layout in timedLayouts"
              :key="layout.item.id"
              class="day-view-time-block"
              :style="timeBlockStyle(layout)"
              @click.stop="openEditDialog(layout.item)"
            >
              <template v-if="layout.item.schedule_type === 'TODO'">
                <span class="todo-box">{{ layout.item.is_todo_completed ? '☑' : '□' }}</span>
                <span :class="{ completed: layout.item.is_todo_completed }">{{
                  scheduleText(layout.item)
                }}</span>
              </template>
              <template v-else>
                <span>{{ scheduleText(layout.item) }}</span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <div
    v-if="showTodoAlertPopup"
    class="todo-alert-backdrop"
    @click.self="closeTodoAlertPopup"
  >
    <section
      class="todo-alert-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="todo-alert-title"
      @click.stop
    >
      <h2 id="todo-alert-title" class="todo-alert-title-h">注意喚起 TODO</h2>
      <p class="todo-alert-lead">
        今日（{{ toDateKey(new Date()) }}）を基準とした注意喚起対象の TODO です。
      </p>
      <p v-if="todoAlertError" class="message error">{{ todoAlertError }}</p>
      <ul class="todo-alert-list">
        <li v-for="item in todoAlerts" :key="item.id" class="todo-alert-li">
          <div v-if="item.is_todo_completed" class="todo-alert-row todo-alert-row--done">
            <span class="todo-alert-check-spacer" aria-hidden="true" />
            <div class="todo-alert-body">
              <span class="todo-alert-item-title todo-alert-item-title--done">{{ item.title }}</span>
              <p v-if="todoAlertWhenLabel(item)" class="todo-alert-meta">{{ todoAlertWhenLabel(item) }}</p>
            </div>
          </div>
          <label v-else class="todo-alert-row">
            <input
              class="todo-alert-checkbox"
              type="checkbox"
              :checked="todoAlertSelectedIds.includes(item.id)"
              :disabled="todoAlertUpdatingBulk"
              @change="onTodoAlertSelectionChange(item.id, $event)"
            />
            <div class="todo-alert-body">
              <span class="todo-alert-item-title">{{ item.title }}</span>
              <p v-if="todoAlertWhenLabel(item)" class="todo-alert-meta">{{ todoAlertWhenLabel(item) }}</p>
            </div>
          </label>
        </li>
      </ul>
      <div class="todo-alert-actions">
        <button
          type="button"
          class="todo-alert-update"
          :disabled="todoAlertSelectedIds.length === 0 || todoAlertUpdatingBulk"
          @click="applyTodoAlertUpdates"
        >
          {{ todoAlertUpdatingBulk ? '更新中…' : '更新' }}
        </button>
        <button
          type="button"
          class="todo-alert-close"
          :disabled="todoAlertUpdatingBulk"
          @click="closeTodoAlertPopup"
        >
          閉じる
        </button>
      </div>
    </section>
  </div>

  <div
    v-if="showMonthSettings"
    class="settings-backdrop"
    @click.self="showMonthSettings = false"
  >
    <section
      class="settings-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="month-settings-title"
      @click.stop
    >
      <h2 id="month-settings-title" class="settings-title">月表示の設定</h2>
      <p v-if="monthSettingsError" class="message error">{{ monthSettingsError }}</p>
      <fieldset class="settings-fieldset" :disabled="monthSettingsSaving">
        <legend class="settings-legend">表示の種類</legend>
        <label class="settings-radio">
          <input
            type="radio"
            name="monthDisplay"
            value="list"
            :checked="monthDisplayMode === 'list'"
            @change="setMonthDisplayMode('list')"
          />
          一覧表示
        </label>
        <label class="settings-radio">
          <input
            type="radio"
            name="monthDisplay"
            value="calendar"
            :checked="monthDisplayMode === 'calendar'"
            @change="setMonthDisplayMode('calendar')"
          />
          カレンダー表示
        </label>
        <label class="settings-radio">
          <input
            type="radio"
            name="monthDisplay"
            value="calendar-pc"
            :checked="monthDisplayMode === 'calendar-pc'"
            @change="setMonthDisplayMode('calendar-pc')"
          />
          カレンダー表示（PC用）
        </label>
      </fieldset>
      <fieldset
        v-if="isCalendarDisplayMode(monthDisplayMode)"
        class="settings-fieldset"
        :disabled="monthSettingsSaving"
      >
        <legend class="settings-legend">週の始まり</legend>
        <label class="settings-radio">
          <input
            type="radio"
            name="weekStart"
            value="sunday"
            :checked="weekStartsOn === 'sunday'"
            @change="setWeekStartsOn('sunday')"
          />
          日曜始まり
        </label>
        <label class="settings-radio">
          <input
            type="radio"
            name="weekStart"
            value="monday"
            :checked="weekStartsOn === 'monday'"
            @change="setWeekStartsOn('monday')"
          />
          月曜始まり
        </label>
      </fieldset>
      <button type="button" class="settings-close" @click="showMonthSettings = false">
        閉じる
      </button>
    </section>
  </div>

  <div v-if="showDialog" class="dialog-backdrop">
    <section class="dialog-card">
      <h2>{{ dialogMode === 'create' ? '新規スケジュール' : 'スケジュール編集' }}</h2>
      <p class="dialog-mode-date" v-if="dialogMode === 'create'">
        日付: {{ selectedDateForCreate }}
      </p>
      <p v-if="formError" class="message error">{{ formError }}</p>

      <label>
        タイトル
        <input v-model="form.title" type="text" />
      </label>

      <label>
        種別
        <select v-model="form.scheduleType">
          <option value="予定">予定</option>
          <option value="TODO">TODO</option>
        </select>
      </label>

      <label>
        カテゴリ
        <select v-model="form.categoryId">
          <option v-for="category in categories" :key="category.id" :value="String(category.id)">
            {{ category.name }}
          </option>
        </select>
      </label>

      <label class="checkbox-line">
        <input v-model="form.isAllDay" type="checkbox" />
        終日
      </label>

      <label>
        開始日
        <span class="dialog-input-clip">
          <input v-model="form.startDate" type="date" />
        </span>
      </label>

      <label v-if="form.isAllDay">
        終了日
        <span class="dialog-input-clip">
          <input v-model="form.endDate" type="date" />
        </span>
      </label>

      <template v-else>
        <label>
          開始時刻
          <span class="dialog-input-clip">
            <input v-model="form.startTime" type="time" />
          </span>
        </label>
        <label>
          終了時刻
          <span class="dialog-input-clip">
            <input v-model="form.endTime" type="time" />
          </span>
        </label>
      </template>

      <label v-if="form.scheduleType === 'TODO'" class="checkbox-line">
        <input v-model="form.isTodoCompleted" type="checkbox" />
        実施済み
      </label>

      <label>
        場所
        <input v-model="form.location" type="text" />
      </label>

      <label>
        詳細
        <textarea v-model="form.details" rows="3" />
      </label>

      <div class="dialog-actions">
        <button type="button" @click="closeDialog">閉じる</button>
        <button type="button" class="primary" @click="saveSchedule">保存</button>
        <button v-if="dialogMode === 'edit'" type="button" class="danger" @click="removeSchedule">
          削除
        </button>
      </div>
    </section>
  </div>
</template>
