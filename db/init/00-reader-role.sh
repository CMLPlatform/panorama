#!/bin/sh
# Create the read-only role that the API uses. Runs once, when the database
# volume is empty. The password comes from PANORAMA_READER_PASSWORD (.env).
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v pw="$PANORAMA_READER_PASSWORD" <<'SQL'
CREATE ROLE panorama_reader LOGIN PASSWORD :'pw';
ALTER ROLE panorama_reader SET default_transaction_read_only = on;
SQL
