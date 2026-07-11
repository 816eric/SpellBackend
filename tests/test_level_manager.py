import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.services.level_manager import LevelManager
from src.models.game import Level, LevelProgress
from src.models.word import SpellingWord
from src.models.user import User

@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory test database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_level(session: Session):
    """Test creating a level."""
    manager = LevelManager(session)
    level = manager.create_level(
        name="Animals",
        description="Learn animal names",
        difficulty=1
    )

    assert level.id is not None
    assert level.name == "Animals"
    assert level.difficulty == 1

def test_add_words_to_level(session: Session):
    """Test adding words to a level."""
    manager = LevelManager(session)

    # Create level
    level = manager.create_level("Animals", "Animals", 1)

    # Create words
    word1 = SpellingWord(text="cat", language="en")
    word2 = SpellingWord(text="dog", language="en")
    session.add_all([word1, word2])
    session.commit()

    # Add to level
    manager.add_words_to_level(level.id, [word1.id, word2.id])

    # Verify
    level_data = manager.get_level_with_words(level.id)
    assert len(level_data["words"]) == 2
    assert level_data["words"][0]["text"] == "cat"

def test_complete_level_awards_stars(session: Session):
    """Test level completion awards stars based on accuracy."""
    manager = LevelManager(session)

    # Create user and level
    user = User(name="test_user")
    session.add(user)
    session.commit()

    level = manager.create_level("Test", "Test", 1)

    # Complete with 100% accuracy
    result = manager.complete_level(user.id, level.id, accuracy=1.0)
    assert result["stars"] == 3

    # Complete with 85% accuracy
    level2 = manager.create_level("Test2", "Test", 1)
    result = manager.complete_level(user.id, level2.id, accuracy=0.85)
    assert result["stars"] == 2
