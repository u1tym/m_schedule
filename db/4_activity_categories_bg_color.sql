-- activity_categories: 背景色カラム追加 + 既存行へ仮色 + 有効名の一意制約

ALTER TABLE calendar.activity_categories
  ADD COLUMN bg_color character varying(64);

-- 既存行へ現行フロントのパレットを id 順で割当
WITH numbered AS (
  SELECT
    id,
    (ARRAY[
      '#e0f2fe',
      '#dcfce7',
      '#fef3c7',
      '#fce7f3',
      '#ede9fe',
      '#ffedd5',
      '#ccfbf1'
    ])[((ROW_NUMBER() OVER (ORDER BY id) - 1) % 7) + 1] AS color
  FROM calendar.activity_categories
)
UPDATE calendar.activity_categories AS c
SET bg_color = numbered.color
FROM numbered
WHERE c.id = numbered.id;

ALTER TABLE calendar.activity_categories
  ALTER COLUMN bg_color SET DEFAULT '#e5e7eb',
  ALTER COLUMN bg_color SET NOT NULL;

-- 未削除カテゴリ間で名前一意
CREATE UNIQUE INDEX IF NOT EXISTS uq_activity_categories_name_active
  ON calendar.activity_categories (name)
  WHERE (is_deleted = false);
