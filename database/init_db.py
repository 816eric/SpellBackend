from sqlmodel import SQLModel, Session, select
from src.db_session import engine

def init_db():
    from src.models import user, word, tag, history, reward, link, game, minigame
    from src.models.game import Level
    from src.models.minigame import MiniGame
    SQLModel.metadata.create_all(engine)

    # Only drop and recreate linking tables with ON DELETE CASCADE if Tag table is empty
    import sqlite3
    db_path = engine.url.database if hasattr(engine.url, 'database') else str(engine.url).split('///')[-1]
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # Additive migration: add columns to the existing tag table if they
        # predate these fields (create_all only creates missing tables, it
        # does not alter existing ones).
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(tag);")}
        if "label_type" not in existing_columns:
            conn.execute("ALTER TABLE tag ADD COLUMN label_type TEXT DEFAULT 'TEACHER';")
            conn.execute("UPDATE tag SET label_type = 'TEACHER' WHERE label_type IS NULL;")
            conn.commit()
        if "spell_date" not in existing_columns:
            conn.execute("ALTER TABLE tag ADD COLUMN spell_date VARCHAR;")
            conn.commit()

        # Additive migration: minigame table predates game_type/native_key.
        minigame_columns = {row[1] for row in conn.execute("PRAGMA table_info(minigame);")}
        if minigame_columns and "game_type" not in minigame_columns:
            conn.execute("ALTER TABLE minigame ADD COLUMN game_type TEXT DEFAULT 'iframe';")
            conn.execute("UPDATE minigame SET game_type = 'iframe' WHERE game_type IS NULL;")
            conn.commit()
        if minigame_columns and "native_key" not in minigame_columns:
            conn.execute("ALTER TABLE minigame ADD COLUMN native_key VARCHAR;")
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

        # Seed the game store catalog if empty
        game_count = session.exec(select(MiniGame)).first()
        if not game_count:
            session.add(MiniGame(
                name="Word Snake",
                description="Eat, grow, survive - answer vocab questions from your own deck to power up.",
                icon="🐍",
                game_type="native",
                native_key="word_snake",
                unlock_cost=50,
                play_cost=10,
            ))
            session.commit()
        else:
            # Earlier seed created Word Snake as an iframe embed of a
            # third-party site; switch it to the built-in native version.
            existing_snake = session.exec(
                select(MiniGame).where(MiniGame.name == "Word Snake")
            ).first()
            if existing_snake and existing_snake.game_type != "native":
                existing_snake.game_type = "native"
                existing_snake.native_key = "word_snake"
                existing_snake.description = (
                    "Eat, grow, survive - answer vocab questions from your "
                    "own deck to power up."
                )
                session.add(existing_snake)
                session.commit()