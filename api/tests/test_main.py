from fastapi.testclient import TestClient
from sqlalchemy import inspect

import main


def test_status_returns_503_when_database_is_down(database_down):
    # Regression: `return {...}, 500` was serialized by FastAPI as a 200 JSON
    # list, so probes never failed even with the database down.
    response = TestClient(main.app).get("/status")
    assert response.status_code == 503
    assert response.json() == {"status": "connection error"}


def test_readiness_returns_503_when_database_is_down(database_down):
    response = TestClient(main.app).get("/readyz")
    assert response.status_code == 503


def test_liveness_does_not_depend_on_the_database(database_down):
    # A database outage must not make Kubernetes restart every API pod.
    response = TestClient(main.app).get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_app_starts_while_the_database_is_down(database_down):
    # Entering the client runs the lifespan; it must not crash the process.
    with TestClient(main.app) as client:
        assert client.get("/livez").status_code == 200
        assert client.get("/readyz").status_code == 503


def test_readiness_succeeds_and_creates_the_schema(database_up):
    response = TestClient(main.app).get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "connection ok"}
    assert "dados" in inspect(main.engine).get_table_names()


def test_readiness_recovers_when_the_database_comes_back(
    database_down, monkeypatch, tmp_path
):
    client = TestClient(main.app)
    assert client.get("/readyz").status_code == 503

    from sqlalchemy import create_engine

    monkeypatch.setattr(
        main, "engine", create_engine(f"sqlite:///{tmp_path / 'later.db'}")
    )
    assert client.get("/readyz").status_code == 200


def test_data_round_trip(database_up):
    client = TestClient(main.app)
    assert client.get("/readyz").status_code == 200
    assert client.post("/dados", params={"info": "hello"}).status_code == 200
    assert [row["info"] for row in client.get("/dados").json()] == ["hello"]
