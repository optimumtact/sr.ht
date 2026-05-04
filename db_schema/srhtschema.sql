docker compose -f docker-compose-dev.yml exec db pg_dump -U hello_flask -n public -O -x --schema-only hello_flask_dev
--
-- PostgreSQL database dump
--

-- Dumped from database version 13.9 (Debian 13.9-1.pgdg110+1)
-- Dumped by pg_dump version 13.9 (Debian 13.9-1.pgdg110+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job (
    id integer NOT NULL,
    priority integer DEFAULT 100,
    status integer NOT NULL,
    tasktype integer NOT NULL,
    pickledclass bytea NOT NULL,
    metadata jsonb,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_id_seq OWNED BY public.job.id;


--
-- Name: job_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_log (
    id integer NOT NULL,
    job_id integer NOT NULL,
    created timestamp without time zone NOT NULL,
    level integer NOT NULL,
    message text NOT NULL
);


--
-- Name: job_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_log_id_seq OWNED BY public.job_log.id;


--
-- Name: pending_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pending_job (
    id integer NOT NULL,
    job_id integer,
    created timestamp with time zone
);


--
-- Name: pending_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pending_job_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pending_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pending_job_id_seq OWNED BY public.pending_job.id;


--
-- Name: upload; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upload (
    id integer NOT NULL,
    user_id integer,
    hash character varying NOT NULL,
    shorthash character varying,
    path character varying NOT NULL,
    created timestamp without time zone,
    original_name character varying(512),
    hidden boolean,
    thumbnail character varying
);


--
-- Name: upload_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.upload_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: upload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.upload_id_seq OWNED BY public.upload.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(128) NOT NULL,
    email character varying(256) NOT NULL,
    admin boolean,
    password character varying,
    created timestamp without time zone,
    "approvalDate" timestamp without time zone,
    "passwordReset" character varying(128),
    "passwordResetExpiry" timestamp without time zone,
    "apiKey" character varying(128),
    comments character varying(512),
    approved boolean,
    rejected boolean
);


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: job id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job ALTER COLUMN id SET DEFAULT nextval('public.job_id_seq'::regclass);


--
-- Name: job_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_log ALTER COLUMN id SET DEFAULT nextval('public.job_log_id_seq'::regclass);


--
-- Name: pending_job id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pending_job ALTER COLUMN id SET DEFAULT nextval('public.pending_job_id_seq'::regclass);


--
-- Name: upload id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload ALTER COLUMN id SET DEFAULT nextval('public.upload_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: job_log job_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_log
    ADD CONSTRAINT job_log_pkey PRIMARY KEY (id);


--
-- Name: job job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);


--
-- Name: pending_job pending_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pending_job
    ADD CONSTRAINT pending_job_pkey PRIMARY KEY (id);


--
-- Name: upload upload_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload
    ADD CONSTRAINT upload_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_job_log_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_log_created ON public.job_log USING btree (created);


--
-- Name: ix_job_log_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_log_job_id ON public.job_log USING btree (job_id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: ix_user_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_username ON public."user" USING btree (username);


--
-- Name: job_log job_log_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_log
    ADD CONSTRAINT job_log_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE CASCADE;


--
-- Name: pending_job pending_job_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pending_job
    ADD CONSTRAINT pending_job_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE CASCADE;


--
-- Name: upload upload_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload
    ADD CONSTRAINT upload_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

