import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine

# The API reads its database settings from the environment (ConfigMap and
# Secret in the cluster). Point it at a port where nothing listens, so the
# default state in tests is "database down".
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "1")
os.environ.setdefault("DB_NAME", "test")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


@pytest.fixture
def database_down(monkeypatch):
    """A PostgreSQL URL that refuses connections, like a database outage."""
    monkeypatch.setattr(
        main,
        "engine",
        create_engine(
            "postgresql://test:test@127.0.0.1:1/test",
            connect_args={"connect_timeout": 2},
        ),
    )
    monkeypatch.setattr(main, "_schema_ready", False)


@pytest.fixture
def database_up(monkeypatch, tmp_path):
    """A real SQL database (SQLite file) standing in for PostgreSQL."""
    monkeypatch.setattr(
        main, "engine", create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    )
    monkeypatch.setattr(main, "_schema_ready", False)
