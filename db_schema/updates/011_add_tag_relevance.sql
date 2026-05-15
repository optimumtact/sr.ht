ALTER TABLE public.tags
    ADD COLUMN IF NOT EXISTS relevance double precision NOT NULL DEFAULT 0;