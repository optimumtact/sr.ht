-- Create a table to store version information if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'schema_version') THEN
        CREATE TABLE schema_version (
            version_id SERIAL PRIMARY KEY,
            version INTEGER NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Insert initial version
        INSERT INTO schema_version (version) VALUES (0);
    END IF;
END $$;

-- Function to get the current version
CREATE OR REPLACE FUNCTION get_current_version() RETURNS INTEGER AS $$
DECLARE
    current_version INTEGER;
BEGIN
    SELECT version INTO current_version FROM schema_version ORDER BY version_id DESC LIMIT 1;
    RETURN current_version;
END $$ LANGUAGE plpgsql;

-- Check the current version before applying changes
DO $$
DECLARE
    current_version INTEGER;
    required_version INTEGER := 1; -- Set the required version for this script
BEGIN
    current_version := get_current_version();

    IF current_version < required_version THEN
        RAISE NOTICE 'Current version is %, applying changes for version %', current_version, required_version;

        -- Place your table alterations here
        ALTER TABLE my_table ADD COLUMN new_column INTEGER;
        -- Add more table alterations as needed

        -- Update the version table after successful alterations
        INSERT INTO schema_version (version) VALUES (required_version);

        RAISE NOTICE 'Schema updated to version %', required_version;
    ELSE
        RAISE NOTICE 'No changes applied. Current version is already % or higher', current_version;
    END IF;
END $$;
