/** 不正・空の bg_color 時に使うデフォルト背景色 */
export const DEFAULT_CATEGORY_BG_COLOR = '#e5e7eb'

const BG_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/

/** API の bg_color を検証し、不正ならデフォルト色を返す */
export const resolveCategoryBgColor = (raw: string | null | undefined): string => {
  const value = (raw ?? '').trim()
  if (!BG_COLOR_PATTERN.test(value)) {
    return DEFAULT_CATEGORY_BG_COLOR
  }
  return value
}

export const isValidCategoryBgColor = (raw: string | null | undefined): boolean => {
  return BG_COLOR_PATTERN.test((raw ?? '').trim())
}
