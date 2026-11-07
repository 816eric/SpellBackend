from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.models.history import LoginHistory, QuizSessionHistory, StudySessionHistory
from src.models.daily_goal import DailyActivity
from src.models.usage import UsageDay
from src.models.user import User
from src.services.analytics_service import build_dashboard

TODAY = date(2026, 11, 1)


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from src.models import user, history, daily_goal, usage, minigame  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _at(days_ago, hour=12):
    d = TODAY - timedelta(days=days_ago)
    return datetime(d.year, d.month, d.day, hour)


def test_counts_activity_and_usage(session):
    session.add(User(name="ANN", created_at=_at(10)))
    session.add(User(name="BOB", created_at=_at(1)))
    session.add(User(name="OLD"))  # predates created_at
    session.add(User(name="GUEST"))
    session.add(User(name="TESTER", is_tester=True))
    session.add(LoginHistory(user_name="ANN", timestamp=_at(0)))
    session.add(LoginHistory(user_name="GUEST", timestamp=_at(0)))
    session.add(StudySessionHistory(user_name="BOB", word="cat", difficulty=3, studied_at=_at(3)))
    session.add(QuizSessionHistory(user_name="BOB", word="cat", is_correct=True, completed_at=_at(3)))
    session.add(QuizSessionHistory(user_name="BOB", word="dog", is_correct=False, completed_at=_at(3)))
    session.add(DailyActivity(user_name="ANN", day=TODAY.isoformat(), kind="words", amount=5))
    session.add(UsageDay(user_name="ANN", day=TODAY.isoformat(), seconds=600))
    session.add(UsageDay(user_name="ANN", day=(TODAY - timedelta(days=2)).isoformat(), seconds=300))
    session.add(UsageDay(user_name="GUEST", day=TODAY.isoformat(), seconds=9999))
    session.commit()

    d = build_dashboard(session, "day", TODAY)
    o = d["overview"]
    assert o["registered"] == 3  # guest + tester excluded
    assert (o["new_7d"], o["new_30d"], o["signup_date_unknown"]) == (1, 2, 1)
    assert (o["dau"], o["wau"], o["mau"]) == (1, 2, 2)
    assert o["never_active"] == 1
    assert o["usage_tracked_since"] == (TODAY - timedelta(days=2)).isoformat()

    ann = next(r for r in d["per_user"] if r["name"] == "ANN")
    assert (ann["today_min"], ann["week_min"], ann["total_min"]) == (10, 15, 15)
    assert d["series"][-1]["usage_minutes"] == 10
    assert len(d["series"]) == 30
    assert d["learning"]["last_7d"] == {"words_studied": 1, "quiz_answers": 2, "quiz_accuracy_pct": 50}
    assert d["daily_goal_users_7d"] == {"words": 1}
    # ANN (10 days old) and BOB (1 day old) have sign-up dates; OLD does not.
    assert [r["eligible"] for r in d["retention"]] == [2, 1, 0]
    assert d["retention"][2]["pct"] is None
    assert not any("GUEST" == r["name"] for r in d["per_user"])


@pytest.mark.parametrize("period,n", [("day", 30), ("week", 12), ("month", 12)])
def test_period_lengths_and_invalid_period(session, period, n):
    assert len(build_dashboard(session, period, TODAY)["series"]) == n
    assert build_dashboard(session, "bogus", TODAY)["period"] == "day"


def test_child_report(session):
    from src.services.report_service import build_child_report
    session.add(User(name="BOB"))
    session.add(User(name="ANN"))
    for i in range(3):  # active today, yesterday, 2 days ago -> streak 3
        session.add(LoginHistory(user_name="BOB", timestamp=_at(i)))
    session.add(UsageDay(user_name="BOB", day=TODAY.isoformat(), seconds=1200))
    session.add(UsageDay(user_name="ANN", day=TODAY.isoformat(), seconds=9999))
    for ok in (False, False, True):
        session.add(QuizSessionHistory(user_name="BOB", word="because", is_correct=ok, completed_at=_at(1)))
    session.add(QuizSessionHistory(user_name="ANN", word="other", is_correct=False, completed_at=_at(1)))
    session.commit()

    r = build_child_report(session, "bob", TODAY)
    assert r["time"]["today_min"] == 20 and r["time"]["streak_days"] == 3
    assert r["learning"]["quiz_accuracy_7d"] == 33
    assert r["hard_words"] == [{"word": "because", "wrong": 2, "attempts": 3}]
    assert len(r["days"]) == 14 and r["days"][-1]["minutes"] == 20
    assert r["time_tracked_since"] == TODAY.isoformat()  # ANN's rows not included
