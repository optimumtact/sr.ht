CREATE TABLE IF NOT EXISTS public.task_schedule (
    id SERIAL PRIMARY KEY,
    tasktype integer NOT NULL,
    cron_expression character varying(128) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    next_run_time timestamp without time zone NOT NULL,
    last_run_time timestamp without time zone,
    created timestamp without time zone NOT NULL,
    updated timestamp without time zone NOT NULL,
    CONSTRAINT uq_task_schedule_tasktype UNIQUE (tasktype)
);

CREATE INDEX IF NOT EXISTS ix_task_schedule_next_run_time
    ON public.task_schedule USING btree (next_run_time);