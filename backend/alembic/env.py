from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401
from app.config import settings
from app.orm import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _sqlite_foreign_key_state(dbapi_connection: object) -> int:
    row = dbapi_connection.execute("PRAGMA foreign_keys").fetchone()
    if row is None:
        raise RuntimeError("SQLite did not return a PRAGMA foreign_keys state")
    return int(row[0])


def _set_sqlite_foreign_keys(dbapi_connection: object, *, enabled: bool) -> None:
    if getattr(dbapi_connection, "in_transaction", False):
        raise RuntimeError(
            "SQLite foreign-key enforcement must be changed outside an active transaction"
        )

    value = "ON" if enabled else "OFF"
    dbapi_connection.execute(f"PRAGMA foreign_keys={value}")

    expected = 1 if enabled else 0
    actual = _sqlite_foreign_key_state(dbapi_connection)
    if actual != expected:
        raise RuntimeError(
            f"SQLite PRAGMA foreign_keys={value} did not take effect; observed {actual}"
        )


def _sqlite_foreign_key_violations(dbapi_connection: object) -> list[tuple]:
    return list(dbapi_connection.execute("PRAGMA foreign_key_check").fetchall())


def _run_sqlite_migrations(connection: object) -> None:
    # Alembic batch mode recreates SQLite tables for operations that SQLite
    # cannot express with ALTER TABLE. Referencing foreign keys must therefore
    # be disabled for the migration connection while a referenced table is
    # rebuilt, then independently checked before the connection is closed.
    dbapi_connection = connection.connection.driver_connection

    preexisting_violations = _sqlite_foreign_key_violations(dbapi_connection)
    if preexisting_violations:
        raise RuntimeError(
            "SQLite foreign-key violations exist before migration: "
            f"{preexisting_violations[:10]!r}"
        )

    _set_sqlite_foreign_keys(dbapi_connection, enabled=False)
    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()

        violations = _sqlite_foreign_key_violations(dbapi_connection)
        if violations:
            raise RuntimeError(
                "SQLite foreign-key violations detected after migration: "
                f"{violations[:10]!r}"
            )
    finally:
        if getattr(dbapi_connection, "in_transaction", False):
            dbapi_connection.rollback()
        _set_sqlite_foreign_keys(dbapi_connection, enabled=True)


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            _run_sqlite_migrations(connection)
            return

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
