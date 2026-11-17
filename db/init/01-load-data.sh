#!/bin/sh
# Load the business data from /docker-entrypoint-initdb.d/data, in name order.
# Supports plain SQL (*.sql), gzipped SQL (*.sql.gz) and pg_dump custom
# format (*.dump). Runs once, when the database volume is empty.
set -eu
DIR=/docker-entrypoint-initdb.d/data
PSQL="psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB"

for f in "$DIR"/*; do
  case "$f" in
    *.sql)    echo "Loading $f"; $PSQL -f "$f" ;;
    *.sql.gz) echo "Loading $f"; gunzip -c "$f" | $PSQL ;;
    *.dump)   echo "Loading $f"; pg_restore --no-owner --no-privileges \
                --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$f" ;;
    *)        echo "Skipping $f" ;;
  esac
done

# The reader role may read the two business schemas, and nothing else.
$PSQL <<'SQL'
GRANT USAGE ON SCHEMA production, diffusion TO panorama_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA production, diffusion TO panorama_reader;
SQL
