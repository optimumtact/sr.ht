ALTER TABLE upload ALTER COLUMN shorthash DROP NOT NULL;
ALTER TABLE upload ADD COLUMN IF NOT EXISTS thumbnail VARCHAR;