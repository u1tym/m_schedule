-- スキーマ作成
CREATE SCHEMA IF NOT EXISTS calendar;

-- テーブル移動
ALTER TABLE public.activity_categories SET SCHEMA calendar;
ALTER TABLE public.holidays SET SCHEMA calendar;
ALTER TABLE public.schedules SET SCHEMA calendar;

