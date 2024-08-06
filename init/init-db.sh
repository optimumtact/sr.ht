#!/bin/bash
set -e

# Environment variables
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-postgres}
DB_NAME=${POSTGRES_DB:-postgres}

# Check if the database is empty
echo "Checking if database is empty..."
if [ "$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")" -eq "0" ]; then
  echo "Database is empty. Importing schema..."
  psql -U "$DB_USER" -d "$DB_NAME" -f /docker-entrypoint-initdb.d/srht.schema
else
  echo "Database is not empty. Skipping schema import."
fi
