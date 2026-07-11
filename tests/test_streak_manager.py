import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta
from src.services.streak_manager import StreakManager
from src.models.user import User
from src.models.reward import RewardHistory
from src.models.game import Level, LevelProgress, LevelWord, Unlockable, UserUnlockable, Challenge, LevelStatistics
from src.models.word import SpellingWord

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all models to ensure they're registered
    from src.models import user, reward, game, word

    # Create all tables
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_get_user_streak_no_activity(session: Session):
    """Test streak for user with no activity."""
    user = User(name="test_user")
    session.add(user)
    session.commit()

    manager = StreakManager(session)
    streak = manager.get_user_streak(user.id)

    assert streak["current_streak"] == 0
    assert streak["last_login"] is None

def test_check_daily_login_first_day(session: Session):
    """Test daily login check on first day."""
    user = User(name="test_user", total_points=100)
    session.add(user)
    session.commit()

    manager = StreakManager(session)
    result = manager.check_daily_login(user.id)

    assert result["ok"] is True
    assert result["streak"] >= 1

def test_revive_streak_insufficient_points(session: Session):
    """Test reviving streak with insufficient points."""
    user = User(name="test_user", total_points=10)
    session.add(user)
    session.commit()

    manager = StreakManager(session)
    result = manager.revive_streak(user.id, points_cost=50)

    assert result["ok"] is False
    assert "Insufficient" in result["message"]

def test_revive_streak_success(session: Session):
    """Test successful streak revival."""
    user = User(name="test_user", total_points=100)
    session.add(user)
    session.commit()

    manager = StreakManager(session)
    result = manager.revive_streak(user.id, points_cost=50)

    assert result["ok"] is True
    assert result["remaining_points"] == 50
