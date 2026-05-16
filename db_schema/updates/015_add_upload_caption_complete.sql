ALTER TABLE public.upload
    ADD COLUMN IF NOT EXISTS caption_complete boolean;

ALTER TABLE public.upload
    ALTER COLUMN caption_complete SET DEFAULT false;

UPDATE public.upload
SET caption_complete = false
WHERE caption_complete IS NULL;

ALTER TABLE public.upload
    ALTER COLUMN caption_complete SET NOT NULL;
