from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.services.achievement_service import AchievementService
from src.services.boss_service import BossService
from src.models.user import User
from src.models.game import Level, LevelProgress
from src.models.reward import RewardHistory


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.models import user, tag, word, link, review_state, reward, game, boss, achievement  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(session, name="TESTUSER", total_points=0):
    user = User(name=name, total_points=total_points)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _complete_levels(session, user, count):
    for i in range(count):
        level = Level(name=f"Level {i}", difficulty=1)
        session.add(level)
        session.commit()
        session.refresh(level)
        session.add(LevelProgress(
            user_id=user.id, level_id=level.id, status="completed",
        ))
    session.commit()


def _add_study_days(session, user_name, count):
    now = datetime.utcnow()
    for i in range(count):
        session.add(RewardHistory(
            user_name=user_name, action="earn", points=1, reason="study",
            timestamp=now - timedelta(days=i),
        ))
    session.commit()


def _ids(achievements, completed_only=False):
    return {
        a["id"] for a in achievements
        if (a["completed"] or not completed_only)
    }


def test_no_achievements_unlocked_for_fresh_user(session: Session):
    _make_user(session)
    svc = AchievementService(session)

    achievements = svc.list_for_user("TESTUSER")

    assert all(a["completed"] is False for a in achievements)
    assert all(a["unlocked_at"] is None for a in achievements)


def test_xp_and_gem_achievements_unlock_from_points(session: Session):
    _make_user(session, total_points=100)
    svc = AchievementService(session)

    achievements = svc.list_for_user("TESTUSER")
    completed = {a["id"] for a in achievements if a["completed"]}

    assert "xp_100" in completed
    assert "first_gem" in completed
    assert all(a["unlocked_at"] for a in achievements if a["id"] in completed)


def test_levels_completed_achievements(session: Session):
    user = _make_user(session)
    _complete_levels(session, user, 5)
    svc = AchievementService(session)

    completed = {a["id"] for a in svc.list_for_user("TESTUSER") if a["completed"]}

    assert "stage_1_complete" in completed
    assert "stage_5_complete" in completed


def test_boss_achievement_unlocks_after_defeat(session: Session):
    _make_user(session)
    BossService(session).defeat("TESTUSER", 1)
    svc = AchievementService(session)

    completed = {a["id"] for a in svc.list_for_user("TESTUSER") if a["completed"]}

    assert "boss_1_defeated" in completed


def test_streak_achievement_unlocks_after_7_days(session: Session):
    user = _make_user(session)
    _add_study_days(session, user.name, 7)
    svc = AchievementService(session)

    completed = {a["id"] for a in svc.list_for_user("TESTUSER") if a["completed"]}

    assert "streak_7" in completed


def test_unlock_is_persisted_and_not_re_timed(session: Session):
    _make_user(session, total_points=100)
    svc = AchievementService(session)

    first = next(a for a in svc.list_for_user("TESTUSER") if a["id"] == "xp_100")
    second = next(a for a in svc.list_for_user("TESTUSER") if a["id"] == "xp_100")

    assert first["unlocked_at"] == second["unlocked_at"]


def test_unknown_user_raises(session: Session):
    svc = AchievementService(session)
    with pytest.raises(ValueError):
        svc.list_for_user("NOBODY")
