DROP INDEX IF EXISTS ix_upload_upload_fts;

ALTER TABLE public.upload
    DROP COLUMN IF EXISTS upload_fts;

ALTER TABLE public.upload
    ADD COLUMN upload_fts tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(original_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(caption, '')), 'B')
    ) STORED;

CREATE INDEX IF NOT EXISTS ix_upload_upload_fts ON public.upload USING gin (upload_fts);