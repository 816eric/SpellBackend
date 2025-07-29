from sqlmodel import SQLModel
from src.db_session import engine

def init_db():
    from src.models import user, word, tag, history, reward
    SQLModel.metadata.create_all(engine)