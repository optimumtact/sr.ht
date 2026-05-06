ALTER TABLE public.job
    ADD COLUMN IF NOT EXISTS timeclaimed timestamp without time zone;

ALTER TABLE public.job
    ADD COLUMN IF NOT EXISTS processid integer;

CREATE INDEX IF NOT EXISTS ix_job_status ON public.job USING btree (status);
