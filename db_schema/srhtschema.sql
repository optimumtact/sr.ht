--
-- PostgreSQL database dump
--

-- Dumped from database version 13.9 (Debian 13.9-1.pgdg110+1)
-- Dumped by pg_dump version 14.12 (Ubuntu 14.12-0ubuntu0.22.04.1)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: upload; Type: TABLE; Schema: public; Owner: hello_flask
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
-- Name: upload_id_seq; Type: SEQUENCE; Schema: public; Owner: hello_flask
--

CREATE SEQUENCE public.upload_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;




--
-- Name: upload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hello_flask
--

ALTER SEQUENCE public.upload_id_seq OWNED BY public.upload.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: hello_flask
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
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: hello_flask
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;




--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hello_flask
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: upload id; Type: DEFAULT; Schema: public; Owner: hello_flask
--

ALTER TABLE ONLY public.upload ALTER COLUMN id SET DEFAULT nextval('public.upload_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: hello_flask
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: upload upload_pkey; Type: CONSTRAINT; Schema: public; Owner: hello_flask
--

ALTER TABLE ONLY public.upload
    ADD CONSTRAINT upload_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: hello_flask
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: hello_flask
--

CREATE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: ix_user_username; Type: INDEX; Schema: public; Owner: hello_flask
--

CREATE INDEX ix_user_username ON public."user" USING btree (username);


--
-- Name: upload upload_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hello_flask
--

ALTER TABLE ONLY public.upload
    ADD CONSTRAINT upload_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

