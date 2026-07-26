from sqlmodel import SQLModel, Session, select
from src.db_session import engine

def init_db():
    from src.models import user, word, tag, history, reward, link, game
    from src.models.game import Level
    SQLModel.metadata.create_all(engine)

    # Only drop and recreate linking tables with ON DELETE CASCADE if Tag table is empty
    import sqlite3
    db_path = engine.url.database if hasattr(engine.url, 'database') else str(engine.url).split('///')[-1]
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # Additive migration: add label_type column to existing tag table
        # if it predates this field (create_all only creates missing tables,
        # it does not alter existing ones).
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(tag);")}
        if "label_type" not in existing_columns:
            conn.execute("ALTER TABLE tag ADD COLUMN label_type TEXT DEFAULT 'TEACHER';")
            conn.execute("UPDATE tag SET label_type = 'TEACHER' WHERE label_type IS NULL;")
            conn.commit()

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

    # Seed default levels if none exist
    with Session(engine) as session:
        level_count = session.exec(select(Level)).first()
        if not level_count:
            # Create default levels
            levels = [
                Level(
                    name="Beginner Basics",
                    description="Learn the basics of spelling with common words",
                    difficulty=1
                ),
                Level(
                    name="Intermediate Words",
                    description="Progress to more challenging vocabulary",
                    difficulty=2
                ),
                Level(
                    name="Advanced Vocabulary",
                    description="Master advanced and complex words",
                    difficulty=3
                ),
                Level(
                    name="Expert Challenge",
                    description="Tackle the most difficult spelling challenges",
                    difficulty=4
                ),
                Level(
                    name="Master Level",
                    description="Become a spelling master",
                    difficulty=5
                ),
            ]
            for level in levels:
                session.add(level)
            session.commit()