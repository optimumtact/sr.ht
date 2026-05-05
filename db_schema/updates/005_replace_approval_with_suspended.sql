ALTER TABLE public."user"
    ADD COLUMN IF NOT EXISTS suspended boolean NOT NULL DEFAULT false;

ALTER TABLE public."user"
    DROP COLUMN IF EXISTS "approvalDate",
    DROP COLUMN IF EXISTS approved,
    DROP COLUMN IF EXISTS rejected;
