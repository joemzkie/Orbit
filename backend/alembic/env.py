from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context

# Make backend modules importable when Alembic runs from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dbconn import Base, database_url  # noqa: E402
from models import comment, idempotency, like, post, user  # noqa: E402, F401


# Read logging settings from Alembic's configuration file when it is available.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the application's environment-derived database URL for migrations.
config.set_main_option("sqlalchemy.url", database_url.render_as_string(hide_password=False))
# Include every imported ORM model in Alembic's schema metadata.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL migration output without opening a database connection."""

    # Configure Alembic with the database URL and ORM schema metadata.
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        # Run the configured migration revisions against generated SQL output.
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations through a live database connection."""

    # Create Alembic's SQLAlchemy engine from the application configuration.
    connectable = context.config.attributes.get("connection", None)
    if connectable is None:
        from sqlalchemy import engine_from_config

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=__import__("sqlalchemy").pool.NullPool,
        )

    with connectable.connect() as connection:
        # Configure schema comparison and execute revisions in one transaction.
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
