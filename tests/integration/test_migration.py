from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_applies_to_clean_database(tmp_path, monkeypatch) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(url)
    inspector = inspect(engine)
    assert "contacts" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("contacts")} == {
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "message",
        "status",
        "idempotency_key",
        "created_at",
        "updated_at",
    }
    engine.dispose()
