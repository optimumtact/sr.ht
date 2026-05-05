ALTER TABLE public.job
    ADD COLUMN IF NOT EXISTS created timestamp without time zone;

UPDATE public.job
SET created = NOW()
WHERE created IS NULL;

CREATE INDEX IF NOT EXISTS ix_job_created ON public.job USING btree (created);
