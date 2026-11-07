import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.models.user import User
from src.models import daily_goal  # noqa: F401
from src.services import daily_goal_service as svc


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(User(name="KID", grade="P1"))
        s.commit()
        yield s


def _round(s):
    for k in ("english", "chinese", "moe"):
        svc.record_activity(s, "KID", k)


def test_no_game_time_before_goals(session):
    svc.record_activity(session, "KID", "practice", 300)
    assert svc.get_status(session, "KID")["playtimeLimitSeconds"] == 0


def test_first_round_gives_10_minutes_whatever_the_practice(session):
    svc.record_activity(session, "KID", "practice", 1500)
    _round(session)
    assert svc.get_status(session, "KID")["playtimeLimitSeconds"] == 600


def test_next_round_equals_practice_time_since(session):
    svc.record_activity(session, "KID", "practice", 400)
    _round(session)
    svc.record_activity(session, "KID", "practice", 240)
    _round(session)
    assert svc.get_status(session, "KID")["playtimeLimitSeconds"] == 600 + 240


def test_extra_per_round_is_under_10_minutes(session):
    _round(session)
    svc.record_activity(session, "KID", "practice", 1500)
    _round(session)
    assert svc.get_status(session, "KID")["playtimeLimitSeconds"] == 600 + 599


def test_practice_without_a_new_round_earns_nothing(session):
    _round(session)
    svc.record_activity(session, "KID", "practice", 500)
    assert svc.get_status(session, "KID")["playtimeLimitSeconds"] == 600
