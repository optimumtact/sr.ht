ALTER TABLE public.upload
    ADD COLUMN IF NOT EXISTS caption TEXT DEFAULT NULL;

ALTER TABLE public.upload
    ADD COLUMN IF NOT EXISTS upload_fts tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(original_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(caption, '')), 'B')
    ) STORED;

ALTER TABLE public.tags
    ADD COLUMN IF NOT EXISTS tag_fts tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(tag, ''))
    ) STORED;

CREATE INDEX IF NOT EXISTS ix_upload_upload_fts ON public.upload USING gin (upload_fts);
CREATE INDEX IF NOT EXISTS ix_tags_tag_fts ON public.tags USING gin (tag_fts);