import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_postgres_connection_strings_use_the_installed_psycopg_driver():
    assert Settings(database_url="postgresql://fleetmind:secret@db.example.test/fleetmind").database_url == (
        "postgresql+psycopg://fleetmind:secret@db.example.test/fleetmind"
    )
    assert Settings(database_url="postgres://fleetmind:secret@db.example.test/fleetmind").database_url == (
        "postgresql+psycopg://fleetmind:secret@db.example.test/fleetmind"
    )
    assert Settings(database_url="postgresql+psycopg://fleetmind:secret@db.example.test/fleetmind").database_url == (
        "postgresql+psycopg://fleetmind:secret@db.example.test/fleetmind"
    )


def test_database_url_is_required_and_cannot_be_empty(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    with pytest.raises(ValidationError):
        Settings(database_url="")
