<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import {
  DEFAULT_CATEGORY_BG_COLOR,
  isValidCategoryBgColor,
  resolveCategoryBgColor,
} from '../categoryColor'
import type { ActivityCategory } from '../types'

const props = defineProps<{
  categories: ActivityCategory[]
  hiddenCategoryIds: number[]
  showDeleted: boolean
}>()

const emit = defineEmits<{
  'update:showDeleted': [value: boolean]
  'toggle-hidden': [categoryId: number]
  changed: []
}>()

const errorMessage = ref('')
const saving = ref(false)
const editingId = ref<number | null>(null)
const draftName = ref('')
const draftColor = ref(DEFAULT_CATEGORY_BG_COLOR)
const creating = ref(false)
const createName = ref('')
const createColor = ref(DEFAULT_CATEGORY_BG_COLOR)

const visibleCategories = computed(() => {
  if (props.showDeleted) {
    return props.categories
  }
  return props.categories.filter((item) => !item.is_deleted)
})

const isHidden = (id: number): boolean => props.hiddenCategoryIds.includes(id)

const startEdit = (item: ActivityCategory, event: MouseEvent): void => {
  event.stopPropagation()
  errorMessage.value = ''
  creating.value = false
  editingId.value = item.id
  draftName.value = item.name
  draftColor.value = resolveCategoryBgColor(item.bg_color)
}

const cancelEdit = (): void => {
  editingId.value = null
  draftName.value = ''
  draftColor.value = DEFAULT_CATEGORY_BG_COLOR
}

const startCreate = (): void => {
  errorMessage.value = ''
  editingId.value = null
  creating.value = true
  createName.value = ''
  createColor.value = DEFAULT_CATEGORY_BG_COLOR
}

const cancelCreate = (): void => {
  creating.value = false
  createName.value = ''
  createColor.value = DEFAULT_CATEGORY_BG_COLOR
}

const saveEdit = async (): Promise<void> => {
  if (editingId.value === null) return
  const name = draftName.value.trim()
  if (!name) {
    errorMessage.value = '名前を入力してください。'
    return
  }
  if (!isValidCategoryBgColor(draftColor.value)) {
    errorMessage.value = '色は #RRGGBB 形式で指定してください。'
    return
  }
  const current = props.categories.find((item) => item.id === editingId.value)
  if (!current) return

  saving.value = true
  errorMessage.value = ''
  try {
    await api.updateActivityCategory(editingId.value, {
      name,
      bg_color: draftColor.value.trim(),
      is_deleted: current.is_deleted,
    })
    cancelEdit()
    emit('changed')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '更新に失敗しました。'
  } finally {
    saving.value = false
  }
}

const saveCreate = async (): Promise<void> => {
  const name = createName.value.trim()
  if (!name) {
    errorMessage.value = '名前を入力してください。'
    return
  }
  if (!isValidCategoryBgColor(createColor.value)) {
    errorMessage.value = '色は #RRGGBB 形式で指定してください。'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    await api.createActivityCategory({
      name,
      bg_color: createColor.value.trim(),
    })
    cancelCreate()
    emit('changed')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '追加に失敗しました。'
  } finally {
    saving.value = false
  }
}

const softDelete = async (item: ActivityCategory, event: MouseEvent): Promise<void> => {
  event.stopPropagation()
  if (item.is_deleted) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.deleteActivityCategory(item.id)
    if (editingId.value === item.id) cancelEdit()
    emit('changed')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '削除に失敗しました。'
  } finally {
    saving.value = false
  }
}

const restore = async (item: ActivityCategory, event: MouseEvent): Promise<void> => {
  event.stopPropagation()
  if (!item.is_deleted) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.updateActivityCategory(item.id, {
      name: item.name,
      bg_color: resolveCategoryBgColor(item.bg_color),
      is_deleted: false,
    })
    emit('changed')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '復活に失敗しました。'
  } finally {
    saving.value = false
  }
}

const onRowClick = (item: ActivityCategory): void => {
  if (item.is_deleted) return
  if (editingId.value === item.id) return
  emit('toggle-hidden', item.id)
}

watch(
  () => props.showDeleted,
  () => {
    errorMessage.value = ''
  },
)
</script>

<template>
  <aside class="pc-category-sidebar" aria-label="カテゴリ一覧">
    <div class="pc-category-sidebar-head">
      <h2 class="pc-category-sidebar-title">カテゴリ</h2>
      <button type="button" class="pc-category-add-btn" :disabled="saving" @click="startCreate">
        追加
      </button>
    </div>

    <label class="pc-category-switch">
      <input
        type="checkbox"
        :checked="showDeleted"
        :disabled="saving"
        @change="emit('update:showDeleted', ($event.target as HTMLInputElement).checked)"
      />
      削除済みを表示
    </label>

    <p v-if="errorMessage" class="message error pc-category-error">{{ errorMessage }}</p>

    <div v-if="creating" class="pc-category-editor">
      <input v-model="createName" type="text" class="pc-category-input" placeholder="カテゴリ名" :disabled="saving" />
      <input v-model="createColor" type="color" class="pc-category-color" :disabled="saving" />
      <input v-model="createColor" type="text" class="pc-category-input pc-category-input--color" :disabled="saving" />
      <div class="pc-category-editor-actions">
        <button type="button" class="pc-category-action primary" :disabled="saving" @click="saveCreate">
          保存
        </button>
        <button type="button" class="pc-category-action" :disabled="saving" @click="cancelCreate">
          取消
        </button>
      </div>
    </div>

    <ul class="pc-category-list">
      <li
        v-for="item in visibleCategories"
        :key="item.id"
        class="pc-category-item"
        :class="{
          'pc-category-item--deleted': item.is_deleted,
          'pc-category-item--hidden': !item.is_deleted && isHidden(item.id),
          'pc-category-item--editing': editingId === item.id,
        }"
      >
        <template v-if="editingId === item.id">
          <div class="pc-category-editor">
            <input v-model="draftName" type="text" class="pc-category-input" :disabled="saving" />
            <input v-model="draftColor" type="color" class="pc-category-color" :disabled="saving" />
            <input
              v-model="draftColor"
              type="text"
              class="pc-category-input pc-category-input--color"
              :disabled="saving"
            />
            <div class="pc-category-editor-actions">
              <button type="button" class="pc-category-action primary" :disabled="saving" @click="saveEdit">
                保存
              </button>
              <button type="button" class="pc-category-action" :disabled="saving" @click="cancelEdit">
                取消
              </button>
            </div>
          </div>
        </template>
        <template v-else>
          <button
            type="button"
            class="pc-category-row"
            :disabled="saving || item.is_deleted"
            :title="item.is_deleted ? '削除済み' : isHidden(item.id) ? '非表示（クリックで表示）' : '表示中（クリックで非表示）'"
            @click="onRowClick(item)"
          >
            <span
              class="pc-category-swatch"
              :style="{ backgroundColor: resolveCategoryBgColor(item.bg_color) }"
              aria-hidden="true"
            />
            <span class="pc-category-name" :class="{ 'pc-category-name--strike': item.is_deleted }">
              {{ item.name }}
            </span>
            <span v-if="!item.is_deleted && isHidden(item.id)" class="pc-category-hidden-mark">非表示</span>
          </button>
          <div class="pc-category-item-actions">
            <button
              v-if="!item.is_deleted"
              type="button"
              class="pc-category-action"
              :disabled="saving"
              @click="startEdit(item, $event)"
            >
              編集
            </button>
            <button
              v-if="!item.is_deleted"
              type="button"
              class="pc-category-action danger"
              :disabled="saving"
              @click="softDelete(item, $event)"
            >
              削除
            </button>
            <button
              v-if="item.is_deleted"
              type="button"
              class="pc-category-action primary"
              :disabled="saving"
              @click="restore(item, $event)"
            >
              復活
            </button>
          </div>
        </template>
      </li>
    </ul>
  </aside>
</template>
