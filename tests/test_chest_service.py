from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.services.chest_service import ChestService, CHEST_REWARD_POINTS
from src.models.user import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.models import user, tag, word, link, review_state, reward  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(session, name="TESTUSER", total_points=0, last_chest_claim_date=None):
    user = User(name=name, total_points=total_points, last_chest_claim_date=last_chest_claim_date)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_chest_available_when_never_claimed(session: Session):
    _make_user(session)
    svc = ChestService(session)
    assert svc.status("TESTUSER") == {"available": True}


def test_claim_grants_points_and_marks_unavailable(session: Session):
    _make_user(session, total_points=10)
    svc = ChestService(session)

    result = svc.claim("TESTUSER")

    assert result["available"] is False
    assert result["points_earned"] == CHEST_REWARD_POINTS
    assert result["total_points"] == 10 + CHEST_REWARD_POINTS
    assert svc.status("TESTUSER") == {"available": False}


def test_double_claim_same_day_is_rejected(session: Session):
    _make_user(session)
    svc = ChestService(session)

    svc.claim("TESTUSER")
    with pytest.raises(ValueError, match="already_claimed"):
        svc.claim("TESTUSER")


def test_chest_available_again_on_a_new_utc_day(session: Session):
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    _make_user(session, last_chest_claim_date=yesterday)
    svc = ChestService(session)

    assert svc.status("TESTUSER") == {"available": True}
    result = svc.claim("TESTUSER")
    assert result["available"] is False


def test_claim_is_case_insensitive_on_username(session: Session):
    _make_user(session, name="GUEST")
    svc = ChestService(session)

    result = svc.claim("guest")

    assert result["points_earned"] == CHEST_REWARD_POINTS
