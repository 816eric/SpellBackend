"""Per-child progress report for the parent view in the app.

Only the signed-in child's own data (the route is guarded by AuthMiddleware so
a token can read only its own /users/{name}/... paths). Nothing here reads
email / phone / age / school: parents see that from what they typed on the
device. Days are UTC calendar dates.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session

from src.services.analytics_service import _ACTIVITY_SQL, _d


def _rows(session: Session, sql: str, **p):
    return session.execute(text(sql), p).fetchall()


def build_child_report(session: Session, name: str, today: Optional[date] = None) -> dict:
    today = today or datetime.utcnow().date()
    u = name.upper()
    d7, d14, d30 = (today - timedelta(days=n) for n in (6, 13, 29))
    prev7 = d7 - timedelta(days=7)

    active = {_d(d) for d, who in _rows(session, _ACTIVITY_SQL) if (who or "").upper() == u} - {None}
    secs = {_d(d): s or 0 for d, s in _rows(
        session, "SELECT day, seconds FROM usageday WHERE UPPER(user_name) = :u", u=u)}
    secs.pop(None, None)

    def minutes(lo: date, hi: date) -> int:
        return round(sum(s for x, s in secs.items() if lo <= x <= hi) / 60)

    # Consecutive active days ending today (or yesterday, if not yet active today).
    streak, cur = 0, today if today in active else today - timedelta(days=1)
    while cur in active:
        streak += 1
        cur -= timedelta(days=1)

    quiz = _rows(
        session,
        "SELECT substr(completed_at,1,10), word, is_correct FROM quizsessionhistory "
        "WHERE UPPER(user_name) = :u AND substr(completed_at,1,10) >= :lo",
        u=u, lo=min(d30, prev7).isoformat())

    def accuracy(lo: date, hi: date):
        rows = [r for r in quiz if lo <= _d(r[0]) <= hi]
        return (round(100 * sum(1 for r in rows if r[2]) / len(rows)), len(rows)) if rows else (None, 0)

    acc7, n7 = accuracy(d7, today)
    acc_prev, _ = accuracy(prev7, d7 - timedelta(days=1))

    missed = defaultdict(lambda: [0, 0])  # word -> [wrong, attempts]
    for day, word, ok in quiz:
        if _d(day) >= d30:
            missed[word][1] += 1
            missed[word][0] += 0 if ok else 1
    hard = sorted(((w, v[0], v[1]) for w, v in missed.items() if v[0] > 0), key=lambda t: (-t[1], t[0]))[:8]

    studied = lambda lo: _rows(
        session,
        "SELECT COUNT(*) FROM studysessionhistory WHERE UPPER(user_name) = :u AND substr(studied_at,1,10) >= :lo",
        u=u, lo=lo.isoformat())[0][0]

    goals = defaultdict(set)
    for kind, day in _rows(
            session, "SELECT kind, day FROM dailyactivity WHERE UPPER(user_name) = :u AND amount > 0 AND day >= :lo",
            u=u, lo=d7.isoformat()):
        goals[kind].add(day)

    points = _rows(session, "SELECT total_points FROM user WHERE UPPER(name) = :u", u=u)
    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "time_tracked_since": min(secs).isoformat() if secs else None,
        "time": {
            "today_min": minutes(today, today),
            "week_min": minutes(d7, today),
            "month_min": minutes(d30, today),
            "active_days_7d": sum(1 for x in active if d7 <= x <= today),
            "active_days_30d": sum(1 for x in active if d30 <= x <= today),
            "streak_days": streak,
            "last_active": max(active).isoformat() if active else None,
        },
        "days": [
            {"day": (d14 + timedelta(days=i)).isoformat(),
             "minutes": minutes(d14 + timedelta(days=i), d14 + timedelta(days=i)),
             "active": (d14 + timedelta(days=i)) in active}
            for i in range(14)
        ],
        "learning": {
            "words_studied_7d": studied(d7),
            "words_studied_30d": studied(d30),
            "quiz_answers_7d": n7,
            "quiz_accuracy_7d": acc7,
            "quiz_accuracy_prev_7d": acc_prev,
        },
        "hard_words": [{"word": w, "wrong": wr, "attempts": at} for w, wr, at in hard],
        "goal_days_7d": {k: len(v) for k, v in sorted(goals.items())},
        "total_points": points[0][0] if points else 0,
    }
