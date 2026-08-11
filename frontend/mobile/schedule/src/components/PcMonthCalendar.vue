<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { WeekStartMode } from '../appSettings'
import type { ScheduleListItem } from '../types'

const HOVER_DELAY_MS = 300
const LONG_PRESS_MS = 300
const CHIP_HEIGHT_PX = 18
const MORE_HEIGHT_PX = 16
const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'] as const

interface PcCalendarCell {
  key: string
  dateKey: string | null
  day: number | null
  inMonth: boolean
  isToday: boolean
  isHoliday: boolean
  holidayName: string
  weekday: number
  items: ScheduleListItem[]
}

const props = defineProps<{
  currentMonth: Date
  weekStartsOn: WeekStartMode
  holidays: Record<string, string>
  schedules: ScheduleListItem[]
  categoryColorMap: Map<number, string>
}>()

const emit = defineEmits<{
  openDay: [dateKey: string]
  openEdit: [item: ScheduleListItem]
  openCreate: [dateKey: string]
}>()

const gridEl = ref<HTMLElement | null>(null)
const bodyHeightByDate = ref<Record<string, number>>({})
const popupOpen = ref(false)
const popupDateKey = ref('')
const popupStyle = ref<Record<string, string>>({})
const popupAnchorEl = ref<HTMLElement | null>(null)

let resizeObserver: ResizeObserver | null = null
let hoverTimer: ReturnType<typeof setTimeout> | null = null
let longPressTimer: ReturnType<typeof setTimeout> | null = null
let closeTimer: ReturnType<typeof setTimeout> | null = null
let longPressOpened = false

const toDateKey = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatClock = (iso: string): string => {
  const date = new Date(iso)
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

const schedulesForDay = (dateKey: string): ScheduleListItem[] => {
  return props.schedules.filter((item) => {
    if (item.is_all_day && item.start_date && item.end_date) {
      return dateKey >= item.start_date && dateKey <= item.end_date
    }
    if (!item.is_all_day && item.start_datetime) {
      return item.start_datetime.slice(0, 10) === dateKey
    }
    return false
  })
}

const compareSchedules = (a: ScheduleListItem, b: ScheduleListItem): number => {
  if (a.is_all_day !== b.is_all_day) {
    return a.is_all_day ? -1 : 1
  }
  if (a.is_all_day && b.is_all_day) {
    return a.title.localeCompare(b.title, 'ja')
  }
  const startA = a.start_datetime || ''
  const startB = b.start_datetime || ''
  if (startA !== startB) {
    return startA < startB ? -1 : 1
  }
  const endA = a.end_datetime || ''
  const endB = b.end_datetime || ''
  if (endA !== endB) {
    return endA < endB ? -1 : 1
  }
  return a.title.localeCompare(b.title, 'ja')
}

const weekdayHeaders = computed((): string[] => {
  if (props.weekStartsOn === 'sunday') {
    return [...WEEKDAYS]
  }
  return [...WEEKDAYS.slice(1), WEEKDAYS[0]]
})

const cells = computed((): PcCalendarCell[] => {
  const year = props.currentMonth.getFullYear()
  const month = props.currentMonth.getMonth()
  const start = new Date(year, month, 1)
  const end = new Date(year, month + 1, 0)
  const daysInMonth = end.getDate()
  const firstWeekday = start.getDay()
  const leadingEmpty =
    props.weekStartsOn === 'sunday' ? firstWeekday : (firstWeekday + 6) % 7
  const todayKey = toDateKey(new Date())
  const result: PcCalendarCell[] = []

  for (let index = 0; index < 42; index += 1) {
    const dayNum = index - leadingEmpty + 1
    if (dayNum < 1 || dayNum > daysInMonth) {
      result.push({
        key: `pad-${index}`,
        dateKey: null,
        day: null,
        inMonth: false,
        isToday: false,
        isHoliday: false,
        holidayName: '',
        weekday: -1,
        items: [],
      })
      continue
    }
    const date = new Date(year, month, dayNum)
    const dateKey = toDateKey(date)
    const holidayName = props.holidays[dateKey] || ''
    const items = schedulesForDay(dateKey).slice().sort(compareSchedules)
    result.push({
      key: dateKey,
      dateKey,
      day: dayNum,
      inMonth: true,
      isToday: dateKey === todayKey,
      isHoliday: Boolean(holidayName),
      holidayName,
      weekday: date.getDay(),
      items,
    })
  }
  return result
})

const popupItems = computed((): ScheduleListItem[] => {
  if (!popupDateKey.value) return []
  return schedulesForDay(popupDateKey.value).slice().sort(compareSchedules)
})

const popupDateLabel = computed(() => {
  if (!popupDateKey.value) return ''
  const date = new Date(`${popupDateKey.value}T00:00:00`)
  const weekday = WEEKDAYS[date.getDay()]
  return `${date.getMonth() + 1}月${date.getDate()}日（${weekday}）`
})

const chipLabel = (item: ScheduleListItem): string => {
  if (item.is_all_day) {
    return item.title
  }
  if (!item.start_datetime) {
    return item.title
  }
  return `${formatClock(item.start_datetime)} ${item.title}`
}

const chipColor = (item: ScheduleListItem): string =>
  props.categoryColorMap.get(item.activity_category_id) || '#f3f4f6'

const visibleCountFor = (dateKey: string, total: number): number => {
  const height = bodyHeightByDate.value[dateKey]
  if (!height || total <= 0) return 0
  if (total * CHIP_HEIGHT_PX <= height) {
    return total
  }
  return Math.max(0, Math.floor((height - MORE_HEIGHT_PX) / CHIP_HEIGHT_PX))
}

const remainingFor = (dateKey: string, total: number): number => {
  const visible = visibleCountFor(dateKey, total)
  return Math.max(0, total - visible)
}

const clearHoverTimer = (): void => {
  if (hoverTimer) {
    clearTimeout(hoverTimer)
    hoverTimer = null
  }
}

const clearLongPressTimer = (): void => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

const clearCloseTimer = (): void => {
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
}

const positionPopup = (anchor: HTMLElement): void => {
  const rect = anchor.getBoundingClientRect()
  const margin = 8
  const width = Math.min(320, window.innerWidth - margin * 2)
  let left = rect.left
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - margin - width
  }
  if (left < margin) left = margin

  const spaceBelow = window.innerHeight - rect.bottom - margin
  const spaceAbove = rect.top - margin
  const preferBelow = spaceBelow >= 160 || spaceBelow >= spaceAbove
  if (preferBelow) {
    popupStyle.value = {
      left: `${left}px`,
      top: `${rect.bottom + 4}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(120, spaceBelow)}px`,
    }
  } else {
    popupStyle.value = {
      left: `${left}px`,
      bottom: `${window.innerHeight - rect.top + 4}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(120, spaceAbove)}px`,
    }
  }
}

const openPopup = (dateKey: string, anchor: HTMLElement): void => {
  clearCloseTimer()
  clearHoverTimer()
  popupDateKey.value = dateKey
  popupAnchorEl.value = anchor
  popupOpen.value = true
  nextTick(() => positionPopup(anchor))
}

const closePopup = (): void => {
  clearHoverTimer()
  clearCloseTimer()
  popupOpen.value = false
  popupDateKey.value = ''
  popupAnchorEl.value = null
}

const scheduleClosePopup = (): void => {
  clearCloseTimer()
  closeTimer = setTimeout(() => {
    closePopup()
  }, 120)
}

const onMoreEnter = (dateKey: string, event: MouseEvent): void => {
  clearCloseTimer()
  clearHoverTimer()
  const anchor = event.currentTarget as HTMLElement
  hoverTimer = setTimeout(() => {
    openPopup(dateKey, anchor)
  }, HOVER_DELAY_MS)
}

const onMoreLeave = (): void => {
  clearHoverTimer()
  scheduleClosePopup()
}

const onPopupEnter = (): void => {
  clearCloseTimer()
}

const onPopupLeave = (): void => {
  scheduleClosePopup()
}

const onMoreTouchStart = (dateKey: string, event: TouchEvent): void => {
  longPressOpened = false
  clearLongPressTimer()
  const anchor = event.currentTarget as HTMLElement
  longPressTimer = setTimeout(() => {
    longPressOpened = true
    openPopup(dateKey, anchor)
  }, LONG_PRESS_MS)
}

const onMoreTouchEnd = (event: TouchEvent): void => {
  clearLongPressTimer()
  if (longPressOpened) {
    event.preventDefault()
  }
}

const onMoreTouchMove = (): void => {
  clearLongPressTimer()
}

const onMoreClick = (event: MouseEvent): void => {
  event.stopPropagation()
  // タッチ長押し後の合成 click は無視
  if (longPressOpened) {
    event.preventDefault()
    longPressOpened = false
  }
}

const onPopupOpenDay = (): void => {
  const dateKey = popupDateKey.value
  if (!dateKey) return
  closePopup()
  emit('openDay', dateKey)
}

const onPopupCreate = (): void => {
  const dateKey = popupDateKey.value
  if (!dateKey) return
  closePopup()
  emit('openCreate', dateKey)
}

const onDayNumberClick = (dateKey: string, event: MouseEvent): void => {
  event.stopPropagation()
  closePopup()
  emit('openDay', dateKey)
}

const onCellBodyClick = (dateKey: string): void => {
  closePopup()
  emit('openCreate', dateKey)
}

const onChipClick = (item: ScheduleListItem, event: MouseEvent): void => {
  event.stopPropagation()
  closePopup()
  emit('openEdit', item)
}

const measureBodies = (): void => {
  if (!gridEl.value) return
  const next: Record<string, number> = {}
  gridEl.value.querySelectorAll<HTMLElement>('[data-pc-cal-body]').forEach((el) => {
    const dateKey = el.dataset.dateKey
    if (!dateKey) return
    next[dateKey] = el.clientHeight
  })
  bodyHeightByDate.value = next
  if (popupOpen.value && popupAnchorEl.value) {
    positionPopup(popupAnchorEl.value)
  }
}

const onWindowChange = (): void => {
  measureBodies()
}

onMounted(() => {
  measureBodies()
  resizeObserver = new ResizeObserver(() => {
    measureBodies()
  })
  if (gridEl.value) {
    resizeObserver.observe(gridEl.value)
  }
  window.addEventListener('resize', onWindowChange)
  window.addEventListener('scroll', onWindowChange, true)
})

onBeforeUnmount(() => {
  clearHoverTimer()
  clearLongPressTimer()
  clearCloseTimer()
  resizeObserver?.disconnect()
  window.removeEventListener('resize', onWindowChange)
  window.removeEventListener('scroll', onWindowChange, true)
})

watch(
  () => [props.currentMonth, props.weekStartsOn, props.schedules, props.holidays],
  async () => {
    await nextTick()
    measureBodies()
  },
  { deep: true },
)
</script>

<template>
  <section class="pc-month-calendar" aria-label="月カレンダー（PC用）">
    <div class="pc-cal-weekdays" role="row">
      <div
        v-for="(label, index) in weekdayHeaders"
        :key="'pc-wd-' + index"
        class="pc-cal-weekday"
        :class="{
          'pc-cal-weekday--sun': weekStartsOn === 'sunday' ? index === 0 : index === 6,
          'pc-cal-weekday--sat': weekStartsOn === 'sunday' ? index === 6 : index === 5,
        }"
        role="columnheader"
      >
        {{ label }}
      </div>
    </div>

    <div ref="gridEl" class="pc-cal-grid" role="grid">
      <template v-for="cell in cells" :key="cell.key">
        <div
          v-if="cell.inMonth && cell.dateKey"
          class="pc-cal-cell"
          :class="{
            'pc-cal-cell--today': cell.isToday,
            'pc-cal-cell--sun': cell.weekday === 0 && !cell.isHoliday,
            'pc-cal-cell--sat': cell.weekday === 6,
            'pc-cal-cell--holiday': cell.isHoliday,
          }"
        >
          <div class="pc-cal-cell-head">
            <button
              type="button"
              class="pc-cal-day-btn"
              :aria-label="`${cell.day}日の日表示を開く`"
              @click="onDayNumberClick(cell.dateKey, $event)"
            >
              <span class="pc-cal-day">{{ cell.day }}</span>
            </button>
            <span v-if="cell.holidayName" class="pc-cal-holiday" :title="cell.holidayName">
              {{ cell.holidayName }}
            </span>
          </div>
          <div
            class="pc-cal-cell-body"
            data-pc-cal-body
            :data-date-key="cell.dateKey"
            @click="onCellBodyClick(cell.dateKey)"
          >
            <button
              v-for="item in cell.items.slice(0, visibleCountFor(cell.dateKey, cell.items.length))"
              :key="`pc-chip-${cell.dateKey}-${item.id}`"
              type="button"
              class="pc-cal-chip"
              :class="{ 'pc-cal-chip--todo-done': item.schedule_type === 'TODO' && item.is_todo_completed }"
              :style="{ backgroundColor: chipColor(item) }"
              :title="chipLabel(item)"
              @click="onChipClick(item, $event)"
            >
              <span v-if="item.schedule_type === 'TODO'" class="pc-cal-chip-check" aria-hidden="true">
                {{ item.is_todo_completed ? '☑' : '□' }}
              </span>
              <span class="pc-cal-chip-text">{{ chipLabel(item) }}</span>
            </button>
            <button
              v-if="remainingFor(cell.dateKey, cell.items.length) > 0"
              type="button"
              class="pc-cal-more"
              :aria-label="`他 ${remainingFor(cell.dateKey, cell.items.length)} 件を表示`"
              @mouseenter="onMoreEnter(cell.dateKey, $event)"
              @mouseleave="onMoreLeave"
              @touchstart.passive="onMoreTouchStart(cell.dateKey, $event)"
              @touchend="onMoreTouchEnd"
              @touchmove.passive="onMoreTouchMove"
              @click="onMoreClick"
            >
              +{{ remainingFor(cell.dateKey, cell.items.length) }}
            </button>
          </div>
        </div>
        <div v-else class="pc-cal-cell pc-cal-cell--pad" aria-hidden="true" />
      </template>
    </div>
  </section>

  <Teleport to="body">
    <div
      v-if="popupOpen"
      class="pc-cal-popup"
      :style="popupStyle"
      role="dialog"
      aria-label="その日の予定一覧"
      @mouseenter="onPopupEnter"
      @mouseleave="onPopupLeave"
    >
      <div class="pc-cal-popup-head">
        <p class="pc-cal-popup-title">{{ popupDateLabel }}</p>
        <button type="button" class="pc-cal-popup-day-link" @click="onPopupOpenDay">
          日表示へ
        </button>
      </div>
      <div v-if="popupItems.length === 0" class="pc-cal-popup-empty">予定・TODOはありません</div>
      <div class="pc-cal-popup-list">
        <button
          v-for="item in popupItems"
          :key="`pc-popup-${item.id}`"
          type="button"
          class="pc-cal-chip pc-cal-chip--popup"
          :class="{ 'pc-cal-chip--todo-done': item.schedule_type === 'TODO' && item.is_todo_completed }"
          :style="{ backgroundColor: chipColor(item) }"
          @click="onChipClick(item, $event)"
        >
          <span v-if="item.schedule_type === 'TODO'" class="pc-cal-chip-check" aria-hidden="true">
            {{ item.is_todo_completed ? '☑' : '□' }}
          </span>
          <span class="pc-cal-chip-text">{{ chipLabel(item) }}</span>
        </button>
      </div>
      <button type="button" class="pc-cal-popup-create" @click="onPopupCreate">
        新規作成
      </button>
    </div>
  </Teleport>
</template>
