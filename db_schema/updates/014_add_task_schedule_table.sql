CREATE TABLE IF NOT EXISTS public.task_schedule (
    id integer NOT NULL,
    tasktype integer NOT NULL,
    cron_expression character varying(128) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    next_run_time timestamp without time zone NOT NULL,
    last_run_time timestamp without time zone,
    created timestamp without time zone NOT NULL,
    updated timestamp without time zone NOT NULL,
    CONSTRAINT uq_task_schedule_tasktype UNIQUE (tasktype)
);

CREATE SEQUENCE IF NOT EXISTS public.task_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.task_schedule_id_seq OWNED BY public.task_schedule.id;

ALTER TABLE ONLY public.task_schedule ALTER COLUMN id SET DEFAULT nextval('public.task_schedule_id_seq'::regclass);

ALTER TABLE ONLY public.task_schedule
    ADD CONSTRAINT task_schedule_pkey PRIMARY KEY (id);

CREATE INDEX IF NOT EXISTS ix_task_schedule_next_run_time
    ON public.task_schedule USING btree (next_run_time);