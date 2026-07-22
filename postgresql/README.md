# LocalOrbit PostgreSQL bootstrap

For a normal PostgreSQL server, run these commands from this repository:

```powershell
psql -U postgres -d postgres -v app_password='use-a-long-random-password' -f postgresql/create_localorbit_database.sql
psql -U localorbit_app -d localorbit -f supabase/schema.sql
```

The first command creates the `localorbit` database and its application role. The second creates every current LocalOrbit table, constraint, index, trigger function, trigger, and Alembic revision record.

For Supabase, do not run `CREATE DATABASE`: each Supabase project already has one. Open **SQL Editor**, paste the contents of `supabase/schema.sql`, and run it.
