#!/bin/sh
set -eu
# Runs only on a NEW volume. Never silently reinitializes an existing database.
runtime_password=$(cat /run/secrets/db_runtime_password)
migrator_password=$(cat /run/secrets/db_migrator_password)
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  -v runtime_password="$runtime_password" -v migrator_password="$migrator_password" <<'SQL'
SELECT format('CREATE ROLE capexly_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', :'migrator_password') \gexec
SELECT format('CREATE ROLE capexly_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', :'runtime_password') \gexec
ALTER DATABASE capexly OWNER TO capexly_migrator;
REVOKE ALL ON DATABASE capexly FROM PUBLIC;
GRANT CONNECT ON DATABASE capexly TO capexly_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO capexly_migrator;
GRANT USAGE ON SCHEMA public TO capexly_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE capexly_migrator REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE capexly_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO capexly_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE capexly_migrator IN SCHEMA public GRANT USAGE ON SEQUENCES TO capexly_runtime;
SQL
unset runtime_password migrator_password
