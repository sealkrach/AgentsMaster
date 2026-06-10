"""Alembic env.py — utilise une connexion SYNC (psycopg2)."""
from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
fileConfig(config.config_file_name)

# Importer tous les modèles pour que Alembic les connaisse
from db.models import Base  # noqa: E402

target_metadata = Base.metadata


def _sync_url(url: str) -> str:
    """Convertit postgresql+asyncpg://... en postgresql://... pour Alembic."""
    return re.sub(r"\+asyncpg", "", url)


def run_migrations_offline() -> None:
    db_url = _sync_url(os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url")))
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    db_url = _sync_url(os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url")))
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = db_url
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
