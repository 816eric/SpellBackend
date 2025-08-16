from sqlmodel import SQLModel
from src.db_session import engine

def init_db():
    from src.models import user, word, tag, history, reward, link
    SQLModel.metadata.create_all(engine)

    # Only drop and recreate linking tables with ON DELETE CASCADE if Tag table is empty
    import sqlite3
    db_path = engine.url.database if hasattr(engine.url, 'database') else str(engine.url).split('///')[-1]
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        tag_count = conn.execute("SELECT COUNT(*) FROM tag;").fetchone()[0]
        if tag_count == 0:
            # Drop and recreate UserTagsLink
            conn.execute("DROP TABLE IF EXISTS usertagslink;")
            conn.execute("""
                CREATE TABLE usertagslink (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    tag_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
                );
            """)
            # Drop and recreate WordTagLink
            conn.execute("DROP TABLE IF EXISTS wordtaglink;")
            conn.execute("""
                CREATE TABLE wordtaglink (
                    id INTEGER PRIMARY KEY,
                    word_id INTEGER,
                    tag_id INTEGER,
                    FOREIGN KEY (word_id) REFERENCES spellingword(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
                );
            """)