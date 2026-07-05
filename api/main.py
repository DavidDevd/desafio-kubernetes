from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import os

app = FastAPI()

DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(DB_URL)

# Create table during startup for the local demo.
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dados (
            id SERIAL PRIMARY KEY,
            info TEXT NOT NULL
        )
    """))
    conn.commit()


@app.get("/status")
def status():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "connection ok"}
    except OperationalError:
        return {"status": "connection error"}, 500


@app.post("/dados")
def inserir(info: str):
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO dados (info) VALUES (:info)"), {"info": info})
        conn.commit()
    return {"message": "inserted successfully"}


@app.get("/dados")
def listar():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM dados"))
        return [{"id": row[0], "info": row[1]} for row in result]

