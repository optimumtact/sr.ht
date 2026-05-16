ALTER TABLE public."user"
    ADD COLUMN IF NOT EXISTS ai_opt_in boolean NOT NULL DEFAULT false;
