-- Run with psql while connected to the server's existing "postgres" database:
-- psql -U postgres -d postgres -v app_password='replace-with-a-long-random-password' -f create_localorbit_database.sql
--
-- The connected PostgreSQL role must have CREATEDB and CREATEROLE permissions.
-- Do not commit the real password to source control or paste it into shared terminals.

\if :{?app_password}
\else
\echo 'Missing app_password. Re-run with -v app_password=...'
\quit
\endif

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'localorbit_app') THEN
        CREATE ROLE localorbit_app LOGIN;
    END IF;
END;
$$;

ALTER ROLE localorbit_app PASSWORD :'app_password';

-- CREATE DATABASE cannot run inside a transaction. \gexec executes it only when absent.
SELECT format(
    'CREATE DATABASE %I OWNER %I ENCODING ''UTF8'' TEMPLATE template0',
    'localorbit',
    'localorbit_app'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'localorbit')
\gexec

-- The following commands configure the database after it exists.
\connect localorbit

ALTER SCHEMA public OWNER TO localorbit_app;
GRANT USAGE, CREATE ON SCHEMA public TO localorbit_app;
GRANT ALL PRIVILEGES ON DATABASE localorbit TO localorbit_app;

-- Next, load the shared Orbit schema into this database:
-- psql -U localorbit_app -d localorbit -f ..\supabase\schema.sql
