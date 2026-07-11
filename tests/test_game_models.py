"""Unit tests for game models (Level, LevelProgress, LevelWord)"""
import pytest
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from pydantic import ValidationError
from src.models.game import Level, LevelProgress, LevelWord, Challenge, LevelStatistics
from src.models.user import User
from src.models.word import SpellingWord


@pytest.fixture
def session():
    """Create a temporary in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session):
    """Create a test user"""
    user = User(name="test_user", age=10, email="test@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_word(session):
    """Create a test word"""
    word = SpellingWord(text="apple", language="en")
    session.add(word)
    session.commit()
    session.refresh(word)
    return word


def test_level_model_creation(session):
    """Test that a Level model can be created without errors"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    assert level.name == "Level 1"
    assert level.description == "First level"
    assert level.difficulty == 1
    assert isinstance(level.created_at, datetime)
    assert isinstance(level.updated_at, datetime)


def test_level_model_persistence(session, test_word):
    """Test that Level model can be persisted to database"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    assert level.id is not None
    assert level.name == "Level 1"

    # Retrieve from database
    retrieved_level = session.query(Level).filter_by(name="Level 1").first()
    assert retrieved_level is not None
    assert retrieved_level.name == "Level 1"


def test_level_progress_model_creation(session, test_user):
    """Test that LevelProgress model can be created without errors"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    progress = LevelProgress(
        user_id=test_user.id,
        level_id=level.id,
        status="in_progress",
        stars_earned=2,
        points_earned=100,
        study_count=3
    )
    assert progress.user_id == test_user.id
    assert progress.level_id == level.id
    assert progress.status == "in_progress"
    assert progress.stars_earned == 2
    assert progress.points_earned == 100
    assert progress.study_count == 3
    assert progress.started_at is None
    assert progress.completed_at is None
    assert isinstance(progress.updated_at, datetime)


def test_level_progress_model_persistence(session, test_user):
    """Test that LevelProgress model can be persisted to database"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    progress = LevelProgress(
        user_id=test_user.id,
        level_id=level.id,
        status="in_progress",
        stars_earned=2,
        points_earned=100,
        study_count=3
    )
    session.add(progress)
    session.commit()
    session.refresh(progress)

    assert progress.id is not None

    # Retrieve from database
    retrieved_progress = session.query(LevelProgress).filter_by(
        user_id=test_user.id,
        level_id=level.id
    ).first()
    assert retrieved_progress is not None
    assert retrieved_progress.points_earned == 100


def test_level_word_model_creation(session, test_word):
    """Test that LevelWord model can be created without errors"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    level_word = LevelWord(
        level_id=level.id,
        word_id=test_word.id,
        position=1
    )
    assert level_word.level_id == level.id
    assert level_word.word_id == test_word.id
    assert level_word.position == 1


def test_level_word_model_persistence(session, test_word):
    """Test that LevelWord model can be persisted to database"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    level_word = LevelWord(
        level_id=level.id,
        word_id=test_word.id,
        position=1
    )
    session.add(level_word)
    session.commit()
    session.refresh(level_word)

    # Retrieve from database
    retrieved_level_word = session.query(LevelWord).filter_by(
        level_id=level.id,
        word_id=test_word.id
    ).first()
    assert retrieved_level_word is not None
    assert retrieved_level_word.position == 1


def test_level_table_creation(session):
    """Test that Level table is created successfully"""
    # Try to query the table
    result = session.query(Level).all()
    assert result == []

    # Add a level and verify it was inserted
    level = Level(name="Test Level", difficulty=1)
    session.add(level)
    session.commit()

    result = session.query(Level).all()
    assert len(result) == 1


def test_level_progress_table_creation(session, test_user):
    """Test that LevelProgress table is created successfully"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    # Try to query the table
    result = session.query(LevelProgress).all()
    assert result == []

    # Add a progress record and verify it was inserted
    progress = LevelProgress(
        user_id=test_user.id,
        level_id=level.id,
        status="completed"
    )
    session.add(progress)
    session.commit()

    result = session.query(LevelProgress).all()
    assert len(result) == 1


def test_level_word_table_creation(session, test_word):
    """Test that LevelWord table is created successfully"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    # Try to query the table
    result = session.query(LevelWord).all()
    assert result == []

    # Add a level-word association and verify it was inserted
    level_word = LevelWord(
        level_id=level.id,
        word_id=test_word.id,
        position=1
    )
    session.add(level_word)
    session.commit()

    result = session.query(LevelWord).all()
    assert len(result) == 1


def test_level_progress_foreign_key_constraint(session, test_user):
    """Test that LevelProgress properly references Level and User"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    progress = LevelProgress(
        user_id=test_user.id,
        level_id=level.id
    )
    session.add(progress)
    session.commit()
    session.refresh(progress)

    # Verify foreign key references work
    retrieved_progress = session.query(LevelProgress).filter_by(id=progress.id).first()
    assert retrieved_progress.user_id == test_user.id
    assert retrieved_progress.level_id == level.id


def test_level_word_foreign_key_constraint(session, test_word):
    """Test that LevelWord properly references Level and SpellingWord"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    level_word = LevelWord(
        level_id=level.id,
        word_id=test_word.id,
        position=1
    )
    session.add(level_word)
    session.commit()
    session.refresh(level_word)

    # Verify foreign key references work
    retrieved_level_word = session.query(LevelWord).filter_by(level_id=level.id, word_id=test_word.id).first()
    assert retrieved_level_word.level_id == level.id
    assert retrieved_level_word.word_id == test_word.id


def test_level_progress_status_field(session, test_user):
    """Test that LevelProgress status field stores correctly"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    # Test different status values
    statuses = ["locked", "in_progress", "completed"]
    for status in statuses:
        progress = LevelProgress(
            user_id=test_user.id,
            level_id=level.id,
            status=status
        )
        session.add(progress)

    session.commit()

    # Verify all statuses are stored correctly
    locked = session.query(LevelProgress).filter_by(status="locked").count()
    in_progress = session.query(LevelProgress).filter_by(status="in_progress").count()
    completed = session.query(LevelProgress).filter_by(status="completed").count()

    assert locked == 1
    assert in_progress == 1
    assert completed == 1


def test_level_difficulty_scale(session):
    """Test that Level difficulty field supports the 1-5 scale"""
    for difficulty in range(1, 6):
        level = Level(name=f"Level {difficulty}", difficulty=difficulty)
        session.add(level)

    session.commit()

    # Verify all difficulty levels were stored
    result = session.query(Level).all()
    assert len(result) == 5

    # Verify they're in order
    for i, level in enumerate(sorted(result, key=lambda l: l.difficulty), 1):
        assert level.difficulty == i


def test_challenge_model_creation(session, test_user):
    """Test that Challenge model can be created without errors"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    # Create another user for challengee
    challenger = test_user
    challengee = User(name="other_user", age=11, email="other@example.com")
    session.add(challengee)
    session.commit()
    session.refresh(challengee)

    challenge = Challenge(
        challenger_id=challenger.id,
        challengee_id=challengee.id,
        level_id=level.id,
        status="pending",
        points_at_stake=20
    )
    assert challenge.challenger_id == challenger.id
    assert challenge.challengee_id == challengee.id
    assert challenge.level_id == level.id
    assert challenge.status == "pending"
    assert challenge.points_at_stake == 20
    assert isinstance(challenge.created_at, datetime)


def test_challenge_model_persistence(session, test_user):
    """Test that Challenge model can be persisted to database"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    challenger = test_user
    challengee = User(name="other_user", age=11, email="other@example.com")
    session.add(challengee)
    session.commit()
    session.refresh(challengee)

    challenge = Challenge(
        challenger_id=challenger.id,
        challengee_id=challengee.id,
        level_id=level.id,
        status="pending"
    )
    session.add(challenge)
    session.commit()
    session.refresh(challenge)

    assert challenge.id is not None

    # Retrieve from database
    retrieved_challenge = session.query(Challenge).filter_by(id=challenge.id).first()
    assert retrieved_challenge is not None
    assert retrieved_challenge.challenger_id == challenger.id
    assert retrieved_challenge.challengee_id == challengee.id


def test_challenge_foreign_key_constraint(session, test_user):
    """Test that Challenge properly references User and Level"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    challenger = test_user
    challengee = User(name="other_user", age=11, email="other@example.com")
    session.add(challengee)
    session.commit()
    session.refresh(challengee)

    challenge = Challenge(
        challenger_id=challenger.id,
        challengee_id=challengee.id,
        level_id=level.id
    )
    session.add(challenge)
    session.commit()
    session.refresh(challenge)

    # Verify foreign key references work
    retrieved_challenge = session.query(Challenge).filter_by(id=challenge.id).first()
    assert retrieved_challenge.challenger_id == challenger.id
    assert retrieved_challenge.challengee_id == challengee.id
    assert retrieved_challenge.level_id == level.id


def test_level_statistics_model_creation(session):
    """Test that LevelStatistics model can be created without errors"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    word = SpellingWord(text="apple", language="en")
    session.add(word)
    session.commit()
    session.refresh(word)

    stats = LevelStatistics(
        level_id=level.id,
        word_id=word.id,
        total_attempts=5,
        correct_attempts=3,
        incorrect_attempts=2
    )
    assert stats.level_id == level.id
    assert stats.word_id == word.id
    assert stats.total_attempts == 5
    assert stats.correct_attempts == 3
    assert stats.incorrect_attempts == 2


def test_level_statistics_model_persistence(session):
    """Test that LevelStatistics model can be persisted to database"""
    level = Level(name="Level 1", description="First level", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    word = SpellingWord(text="apple", language="en")
    session.add(word)
    session.commit()
    session.refresh(word)

    stats = LevelStatistics(
        level_id=level.id,
        word_id=word.id,
        total_attempts=10,
        correct_attempts=8
    )
    session.add(stats)
    session.commit()
    session.refresh(stats)

    assert stats.id is not None

    # Retrieve from database
    retrieved_stats = session.query(LevelStatistics).filter_by(
        level_id=level.id,
        word_id=word.id
    ).first()
    assert retrieved_stats is not None
    assert retrieved_stats.total_attempts == 10
    assert retrieved_stats.correct_attempts == 8


def test_level_statistics_foreign_key_constraint(session):
    """Test that LevelStatistics properly references Level and SpellingWord"""
    level = Level(name="Level 1", difficulty=1)
    session.add(level)
    session.commit()
    session.refresh(level)

    word = SpellingWord(text="apple", language="en")
    session.add(word)
    session.commit()
    session.refresh(word)

    stats = LevelStatistics(
        level_id=level.id,
        word_id=word.id
    )
    session.add(stats)
    session.commit()
    session.refresh(stats)

    # Verify foreign key references work
    retrieved_stats = session.query(LevelStatistics).filter_by(id=stats.id).first()
    assert retrieved_stats.level_id == level.id
    assert retrieved_stats.word_id == word.id


def test_level_difficulty_below_minimum(session):
    """Test that Level difficulty < 1 raises ValidationError"""
    with pytest.raises(ValidationError):
        Level.model_validate({"name": "Invalid Level", "difficulty": 0})


def test_level_difficulty_above_maximum(session):
    """Test that Level difficulty > 5 raises ValidationError"""
    with pytest.raises(ValidationError):
        Level.model_validate({"name": "Invalid Level", "difficulty": 6})


def test_level_progress_stars_below_minimum(session, test_user):
    """Test that LevelProgress stars_earned < 0 raises ValidationError"""
    with pytest.raises(ValidationError):
        LevelProgress.model_validate({
            "user_id": test_user.id,
            "level_id": 1,
            "stars_earned": -1
        })


def test_level_progress_stars_above_maximum(session, test_user):
    """Test that LevelProgress stars_earned > 3 raises ValidationError"""
    with pytest.raises(ValidationError):
        LevelProgress.model_validate({
            "user_id": test_user.id,
            "level_id": 1,
            "stars_earned": 4
        })
