
from sqlmodel import create_engine, Session
from pathlib import Path

def get_db_path():
    # 2) Fly.io volume mount (as set in fly.toml -> destination="/database")
    if Path("/database").is_dir():
        print("Using Fly.io volume mount for database")
        return Path("/database/db.sqlite3")
    # 1) Local development
    print("Using local development database path")
    return Path("database/db.sqlite3")

DB_PATH = get_db_path()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)

def get_session():
    return Session(engine)

def init_db():
    from database.init_db import init_db as _init_db
    _init_db()