import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.persistence.tables import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_OWNER_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="rof12",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section) or {}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS rof12"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS rof12.alembic_version (version_num VARCHAR(128) NOT NULL PRIMARY KEY)"))
        connection.execute(text("ALTER TABLE rof12.alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, version_table_schema="rof12")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

