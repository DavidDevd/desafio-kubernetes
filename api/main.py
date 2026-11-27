import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(DB_URL, pool_pre_ping=True)

# The schema is created once the database first answers, not at import time:
# importing the module never needs a database, so the process starts even
# while PostgreSQL is still booting (no CrashLoopBackOff) and tests can run
# without a real database.
_schema_ready = False


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS dados (
                    id SERIAL PRIMARY KEY,
                    info TEXT NOT NULL
                )
                """
            )
        )


def database_ready() -> bool:
    """True when the database answers and the schema exists."""
    global _schema_ready
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        if not _schema_ready:
            ensure_schema()
            _schema_ready = True
        return True
    except SQLAlchemyError:
        return False


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Best effort: if the database is not up yet, readiness creates the
    # schema later and keeps the pod out of the Service until then.
    database_ready()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/livez")
def livez():
    """Liveness: only proves the process answers.

    It deliberately never touches the database. If it did, a database outage
    would make Kubernetes restart every API pod at once.
    """
    return {"status": "alive"}


def _readiness():
    if database_ready():
        return {"status": "connection ok"}
    # Returning a tuple like Flask (`return body, 500`) does not set the status
    # in FastAPI: it is serialized as a 200 JSON list. JSONResponse does.
    return JSONResponse(status_code=503, content={"status": "connection error"})


@app.get("/readyz")
def readyz():
    """Readiness: the pod only receives traffic when the database answers."""
    return _readiness()


@app.get("/status")
def status():
    """Kept for compatibility; same contract as /readyz."""
    return _readiness()


@app.post("/dados")
def inserir(info: str):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO dados (info) VALUES (:info)"), {"info": info})
    return {"message": "inserted successfully"}


@app.get("/dados")
def listar():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM dados"))
        return [{"id": row[0], "info": row[1]} for row in result]
