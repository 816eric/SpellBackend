
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
    """Returns a plain Session for manual `with get_session() as session:`
    use (Session itself is a context manager, so this closes correctly)."""
    return Session(engine)


def get_session_dep():
    """FastAPI dependency (`Depends(get_session_dep)`): yields a session and
    always closes it afterward. Routes previously used `Depends(get_session)`,
    but a bare `return Session(engine)` as a FastAPI dependency is never
    closed by FastAPI - only a generator dependency gets its cleanup code
    (after the yield) run - so every such request leaked a pooled
    connection until the pool filled up and all DB requests started
    hanging."""
    with Session(engine) as session:
        yield session

def init_db():
    from database.init_db import init_db as _init_db
    _init_db()