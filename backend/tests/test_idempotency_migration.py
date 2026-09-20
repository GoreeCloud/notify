from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

from app.database import build_engine


def _upgrade(database_url: str, revision: str = "head") -> None:
    env = os.environ.copy()
    env["GOREECLOUD_NOTIFY_DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _assert_idempotency_schema(database_url: str) -> None:
    inspector = inspect(create_engine(database_url))

    assert "idempotency_digest" in {
        column["name"] for column in inspector.get_columns("notifications")
    }

    constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("notifications")
    }
    assert constraints["uq_notification_source_idempotency"] == (
        "source_id",
        "idempotency_digest",
    )


def test_idempotency_migration_is_sqlite_portable_and_source_scoped(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'idempotency.db'}"
    _upgrade(database_url, "0005_login_abuse_controls")

    before = inspect(create_engine(database_url))
    assert "idempotency_digest" not in {
        column["name"] for column in before.get_columns("notifications")
    }

    _upgrade(database_url)
    _assert_idempotency_schema(database_url)


def test_idempotency_migration_preserves_existing_notification_delivery_fk(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'idempotency-with-delivery.db'}"
    _upgrade(database_url, "0005_login_abuse_controls")

    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

            connection.execute(
                text(
                    """
                    INSERT INTO service_identities
                        (name, description, enabled, created_at)
                    VALUES
                        ('Existing producer', NULL, 1, CURRENT_TIMESTAMP)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO sources
                        (service_identity_id, slug, name, created_at)
                    VALUES
                        (
                            (SELECT id FROM service_identities WHERE name='Existing producer'),
                            'existing-producer',
                            'Existing Producer',
                            CURRENT_TIMESTAMP
                        )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO channels
                        (slug, name, description, created_at)
                    VALUES
                        ('existing-channel', 'Existing Channel', NULL, CURRENT_TIMESTAMP)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO users
                        (
                            username,
                            display_name,
                            password_hash,
                            is_active,
                            is_admin,
                            created_at
                        )
                    VALUES
                        (
                            'existing-user',
                            'Existing User',
                            NULL,
                            1,
                            0,
                            CURRENT_TIMESTAMP
                        )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO notifications
                        (
                            source_id,
                            channel_id,
                            title,
                            body,
                            severity,
                            created_at,
                            expires_at
                        )
                    VALUES
                        (
                            (SELECT id FROM sources WHERE slug='existing-producer'),
                            (SELECT id FROM channels WHERE slug='existing-channel'),
                            'Existing notification',
                            'Preserve this notification through migration.',
                            'warning',
                            CURRENT_TIMESTAMP,
                            NULL
                        )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO deliveries
                        (
                            notification_id,
                            user_id,
                            device_id,
                            read_at,
                            acknowledged_at,
                            created_at
                        )
                    VALUES
                        (
                            (
                                SELECT id
                                FROM notifications
                                WHERE title='Existing notification'
                            ),
                            (SELECT id FROM users WHERE username='existing-user'),
                            NULL,
                            NULL,
                            NULL,
                            CURRENT_TIMESTAMP
                        )
                    """
                )
            )

        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
            assert connection.execute(
                text("SELECT COUNT(*) FROM notifications")
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM deliveries")
            ).scalar_one() == 1
    finally:
        engine.dispose()

    _upgrade(database_url)
    _assert_idempotency_schema(database_url)

    migrated = build_engine(database_url)
    try:
        with migrated.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []

            notification = connection.execute(
                text(
                    """
                    SELECT id, source_id, channel_id, title, body, severity, idempotency_digest
                    FROM notifications
                    WHERE title='Existing notification'
                    """
                )
            ).mappings().one()
            delivery = connection.execute(
                text(
                    """
                    SELECT notification_id, user_id
                    FROM deliveries
                    """
                )
            ).mappings().one()

            assert notification["body"] == "Preserve this notification through migration."
            assert notification["severity"] == "warning"
            assert notification["idempotency_digest"] is None
            assert delivery["notification_id"] == notification["id"]

            assert connection.execute(
                text("SELECT COUNT(*) FROM notifications")
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM deliveries")
            ).scalar_one() == 1
    finally:
        migrated.dispose()
