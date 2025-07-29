from sqlmodel import create_engine, Session

from config.settings import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)

def get_session():
    return Session(engine)

def init_db():
    from database.init_db import init_db as _init_db
    _init_db()