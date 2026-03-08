from __future__ import annotations

from logging.config import fileConfig
from os import getenv

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _build_url() -> str:
    host = getenv("POSTGRESQL_HOST", "localhost")
    port = getenv("POSTGRESQL_PORT", "5432")
    user = getenv("POSTGRESQL_USER", "postgres")
    password = getenv("POSTGRESQL_PASSWORD", "postgres")
    dbname = getenv("POSTGRESQL_DBNAME", "default_db")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


config.set_main_option("sqlalchemy.url", _build_url())

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
