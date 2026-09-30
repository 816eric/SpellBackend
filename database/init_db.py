from sqlmodel import SQLModel, Session, select
from src.db_session import engine

def init_db():
    from src.models import user, word, tag, history, reward, link, game, minigame, review_state, boss, achievement, checkpoint_progress
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

        # Additive migration: spellingword table predates the MOE Chinese
        # Word Cards pinyin/meaning columns.
        existing_word_columns = {row[1] for row in conn.execute("PRAGMA table_info(spellingword);")}
        if "pinyin" not in existing_word_columns:
            conn.execute("ALTER TABLE spellingword ADD COLUMN pinyin VARCHAR;")
            conn.commit()
        if "meaning" not in existing_word_columns:
            conn.execute("ALTER TABLE spellingword ADD COLUMN meaning VARCHAR;")
            conn.commit()

        existing_review_state_columns = {row[1] for row in conn.execute("PRAGMA table_info(reviewstate);")}
        if "fail_count" not in existing_review_state_columns:
            conn.execute("ALTER TABLE reviewstate ADD COLUMN fail_count INTEGER DEFAULT 0;")
            conn.commit()

        # Additive migration: user table predates the daily minigame
        # playtime cap columns.
        existing_user_columns = {row[1] for row in conn.execute("PRAGMA table_info(user);")}
        if "playtime_seconds_today" not in existing_user_columns:
            conn.execute("ALTER TABLE user ADD COLUMN playtime_seconds_today INTEGER DEFAULT 0;")
            conn.commit()
        if "playtime_date" not in existing_user_columns:
            conn.execute("ALTER TABLE user ADD COLUMN playtime_date VARCHAR;")
            conn.commit()
        if "last_chest_claim_date" not in existing_user_columns:
            conn.execute("ALTER TABLE user ADD COLUMN last_chest_claim_date VARCHAR;")
            conn.commit()

        # Additive migration: user table predates the coins/gems currency
        # split (previously everything was just total_points). Backfill
        # coins = total_points ONE TIME, right here inside the
        # column-doesn't-exist-yet branch, so it runs exactly once at
        # column-creation time. Do NOT move this backfill outside this
        # branch - on every later startup this column already exists, the
        # branch is skipped, and coins is left alone (it may have since been
        # spent, and re-running the backfill would wrongly reset it back to
        # the user's current XP).
        if "coins" not in existing_user_columns:
            conn.execute("ALTER TABLE user ADD COLUMN coins INTEGER DEFAULT 0;")
            conn.execute("UPDATE user SET coins = total_points;")
            conn.commit()
        if "gems" not in existing_user_columns:
            conn.execute("ALTER TABLE user ADD COLUMN gems INTEGER DEFAULT 0;")
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

        # Idempotent: add Word Wheel if this catalog predates it (the
        # `if not game_count` branch above only fires for a brand-new,
        # fully empty table).
        existing_wheel = session.exec(
            select(MiniGame).where(MiniGame.name == "Word Wheel")
        ).first()
        if not existing_wheel:
            session.add(MiniGame(
                name="Word Wheel",
                description="Trace letters to spell your practicing words and fill the crossword.",
                icon="🎡",
                game_type="native",
                native_key="word_wheel",
                unlock_cost=50,
                play_cost=10,
            ))
            session.commit()

        existing_dog = session.exec(
            select(MiniGame).where(MiniGame.name == "Flying Dog Reading")
        ).first()
        if not existing_dog:
            session.add(MiniGame(
                name="Flying Dog Reading",
                description="Read a story out loud to keep the flying dog above the sea.",
                icon="🐕",
                game_type="native",
                native_key="flying_dog_reading",
                unlock_cost=50,
                play_cost=10,
            ))
            session.commit()

        # Idempotent MOE (Singapore) curriculum word-card seed, P1-P6. Safe
        # to run on every startup: checks for existing words/tags/links
        # before inserting anything, so this is a fast no-op after the
        # first run. This is what makes a fresh production DB (e.g. a new
        # Fly volume) get populated automatically on deploy, with no manual
        # seed step required.
        from database.seed_moe_words import seed_all_moe_words
        seed_all_moe_words(session)