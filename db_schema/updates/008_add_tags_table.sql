CREATE TABLE IF NOT EXISTS public.tags (
    id SERIAL PRIMARY KEY,
    uploadid integer NOT NULL,
    tag character varying(128) NOT NULL,
    created timestamp without time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT tags_uploadid_fkey FOREIGN KEY (uploadid) REFERENCES public.upload(id) ON DELETE CASCADE,
    CONSTRAINT uq_tags_uploadid_tag UNIQUE (uploadid, tag)
);

CREATE INDEX IF NOT EXISTS ix_tags_uploadid ON public.tags USING btree (uploadid);
CREATE INDEX IF NOT EXISTS ix_tags_tag ON public.tags USING btree (tag);
