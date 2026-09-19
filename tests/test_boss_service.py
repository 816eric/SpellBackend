import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.services.boss_service import BossService, BOSS_REWARD_POINTS
from src.models.user import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.models import user, tag, word, link, review_state, reward, game, boss  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(session, name="TESTUSER", total_points=0):
    user = User(name=name, total_points=total_points)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_defeat_grants_points_first_time(session: Session):
    _make_user(session)
    svc = BossService(session)

    result = svc.defeat("TESTUSER", 1)

    assert result["first_time"] is True
    assert result["points_earned"] == BOSS_REWARD_POINTS[1]
    assert result["total_points"] == BOSS_REWARD_POINTS[1]
    assert svc.defeated_boss_ids("TESTUSER") == [1]


def test_repeat_defeat_grants_no_additional_points(session: Session):
    _make_user(session)
    svc = BossService(session)

    svc.defeat("TESTUSER", 1)
    result = svc.defeat("TESTUSER", 1)

    assert result["first_time"] is False
    assert result["points_earned"] == 0
    assert result["total_points"] == BOSS_REWARD_POINTS[1]
    assert svc.defeated_boss_ids("TESTUSER") == [1]


def test_unknown_user_raises(session: Session):
    svc = BossService(session)
    with pytest.raises(ValueError):
        svc.defeat("NOBODY", 1)


def test_defeating_multiple_bosses_tracks_each(session: Session):
    _make_user(session)
    svc = BossService(session)

    svc.defeat("TESTUSER", 1)
    svc.defeat("TESTUSER", 2)

    assert svc.defeated_boss_ids("TESTUSER") == [1, 2]
