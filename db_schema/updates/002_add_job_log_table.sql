CREATE TABLE IF NOT EXISTS public.job_log (
    id serial PRIMARY KEY,
    job_id integer NOT NULL REFERENCES public.job (id) ON DELETE CASCADE,
    created timestamp without time zone NOT NULL,
    level integer NOT NULL,
    message text NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_job_log_job_id ON public.job_log USING btree (job_id);
CREATE INDEX IF NOT EXISTS ix_job_log_created ON public.job_log USING btree (created);
