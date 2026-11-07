"""Aggregate usage statistics for the admin dashboard.

Privacy: everything here is derived from data the app already keeps for the
account itself (sign-up time, logins, study/quiz events, daily goals) plus
the per-day foreground-seconds counter in `usageday`. Nothing is read from
email / phone / age / school / password, and results are aggregates or
per-account rows keyed by an internal id (names are shown only when the admin
asks for them).

Days are UTC calendar dates (YYYY-MM-DD). The shared GUEST account and test
accounts are excluded from every figure.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlmodel import Session

# One row per (day, user) on which the account did anything at all.
_ACTIVITY_SQL = """
SELECT substr(timestamp, 1, 10) AS d, user_name AS u FROM loginhistory
UNION SELECT day, user_name FROM usageday WHERE seconds > 0
UNION SELECT substr(studied_at, 1, 10), user_name FROM studysessionhistory
UNION SELECT substr(completed_at, 1, 10), user_name FROM quizsessionhistory
UNION SELECT day, user_name FROM dailyactivity
"""

PERIODS = {"day": 30, "week": 12, "month": 12}


def _d(s: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(s[:10]) if s else None
    except ValueError:
        return None


def _rows(session: Session, sql: str, **params) -> list:
    return session.execute(text(sql), params).fetchall()


def _real_users(session: Session) -> Dict[str, dict]:
    """name -> {id, created} for every non-guest, non-test account."""
    out = {}
    for uid, name, created in _rows(
        session,
        "SELECT id, name, created_at FROM user WHERE UPPER(name) != 'GUEST' AND COALESCE(is_tester, 0) = 0",
    ):
        out[name.upper()] = {"id": uid, "created": _d(created)}
    return out


def _bucket_start(d: date, period: str) -> date:
    if period == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if period == "month":
        return d.replace(day=1)
    return d


def _next_start(start: date, period: str) -> date:
    if period == "week":
        return start + timedelta(days=7)
    if period == "month":
        return (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start + timedelta(days=1)


def _bucket_starts(today: date, period: str) -> List[date]:
    n = PERIODS[period]
    starts = [_bucket_start(today, period)]
    while len(starts) < n:
        prev = starts[0] - timedelta(days=1)
        starts.insert(0, _bucket_start(prev, period))
    return starts


def _label(start: date, period: str) -> str:
    if period == "month":
        return start.strftime("%b %Y")
    return start.strftime("%m-%d")


def build_dashboard(session: Session, period: str = "day", today: Optional[date] = None) -> dict:
    period = period if period in PERIODS else "day"
    today = today or datetime.utcnow().date()
    users = _real_users(session)
    names = set(users)

    activity: Dict[str, Set[date]] = defaultdict(set)  # user -> active days
    for d, u in _rows(session, _ACTIVITY_SQL):
        day, u = _d(d), (u or "").upper()
        if day and u in names:
            activity[u].add(day)

    usage: Dict[str, Dict[date, int]] = defaultdict(dict)  # user -> day -> seconds
    tracked_since = None
    for u, d, s in _rows(session, "SELECT user_name, day, seconds FROM usageday"):
        day, u = _d(d), (u or "").upper()
        if day and u in names:
            usage[u][day] = s or 0
            tracked_since = min(tracked_since, day) if tracked_since else day

    def active_between(lo: date, hi: date) -> Set[str]:
        return {u for u, days in activity.items() if any(lo <= x <= hi for x in days)}

    def seconds_between(u: str, lo: date, hi: date) -> int:
        return sum(s for x, s in usage.get(u, {}).items() if lo <= x <= hi)

    d7, d30 = today - timedelta(days=6), today - timedelta(days=29)
    dau, wau, mau = (len(active_between(lo, today)) for lo in (today, d7, d30))
    total = len(users)
    created_known = [u for u in users.values() if u["created"]]

    overview = {
        "registered": total,
        "new_7d": sum(1 for u in created_known if u["created"] >= d7),
        "new_30d": sum(1 for u in created_known if u["created"] >= d30),
        "signup_date_unknown": total - len(created_known),
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "stickiness_pct": round(100 * dau / mau) if mau else 0,
        "inactive_30d": total - mau,
        "never_active": sum(1 for u in users if not activity.get(u)),
        "usage_tracked_since": tracked_since.isoformat() if tracked_since else None,
    }

    # ---- trend series (day / week / month)
    starts = _bucket_starts(today, period)
    series = []
    for st in starts:
        en = min(_next_start(st, period) - timedelta(days=1), today)
        act = active_between(st, en)
        secs = {u: seconds_between(u, st, en) for u in names}
        users_with_time = [s for s in secs.values() if s > 0]
        total_secs = sum(users_with_time)
        series.append({
            "label": _label(st, period),
            "start": st.isoformat(),
            "active_users": len(act),
            "new_users": sum(1 for u in created_known if st <= u["created"] <= en),
            "usage_minutes": round(total_secs / 60),
            "avg_minutes_per_user": round(total_secs / 60 / len(users_with_time), 1) if users_with_time else 0,
        })

    # ---- per-user time (internal id; the template decides whether to show names)
    per_user = []
    for u, info in users.items():
        days = activity.get(u, set())
        t30 = seconds_between(u, d30, today)
        per_user.append({
            "id": info["id"],
            "name": u,
            "today_min": round(seconds_between(u, today, today) / 60),
            "week_min": round(seconds_between(u, d7, today) / 60),
            "month_min": round(t30 / 60),
            "total_min": round(sum(usage.get(u, {}).values()) / 60),
            "active_days_30d": sum(1 for x in days if d30 <= x <= today),
            "last_active": max(days).isoformat() if days else None,
            "signed_up": info["created"].isoformat() if info["created"] else None,
        })
    per_user.sort(key=lambda r: (r["month_min"], r["week_min"], r["active_days_30d"]), reverse=True)

    # ---- time-spent distribution (last 7 days, accounts with any tracked time)
    buckets = [("under 5 min", 0, 5), ("5-15 min", 5, 15), ("15-30 min", 15, 30),
               ("30-60 min", 30, 60), ("over 60 min", 60, 10**9)]
    week_mins = [r["week_min"] for r in per_user if r["week_min"] > 0]
    distribution = [{"label": l, "users": sum(1 for m in week_mins if lo <= m < hi)} for l, lo, hi in buckets]

    # ---- retention: of accounts old enough, how many were active exactly N days after sign-up
    retention = []
    for n in (1, 7, 30):
        eligible = [u for u, i in users.items() if i["created"] and i["created"] + timedelta(days=n) <= today]
        kept = sum(1 for u in eligible if users[u]["created"] + timedelta(days=n) in activity.get(u, set()))
        retention.append({"day": n, "eligible": len(eligible), "returned": kept,
                          "pct": round(100 * kept / len(eligible)) if eligible else None})

    # ---- learning activity (last 7 and 30 days)
    def learning(lo: date) -> dict:
        lo_s = lo.isoformat()
        studied = _rows(session, "SELECT user_name, COUNT(*) FROM studysessionhistory WHERE substr(studied_at,1,10) >= :lo GROUP BY user_name", lo=lo_s)
        quiz = _rows(session, "SELECT user_name, COUNT(*), SUM(is_correct) FROM quizsessionhistory WHERE substr(completed_at,1,10) >= :lo GROUP BY user_name", lo=lo_s)
        q_total = sum(c for u, c, _ in quiz if (u or "").upper() in names)
        q_ok = sum((ok or 0) for u, _, ok in quiz if (u or "").upper() in names)
        return {
            "words_studied": sum(c for u, c in studied if (u or "").upper() in names),
            "quiz_answers": q_total,
            "quiz_accuracy_pct": round(100 * q_ok / q_total) if q_total else None,
        }

    goals = defaultdict(set)
    for u, kind in _rows(session, "SELECT DISTINCT user_name, kind FROM dailyactivity WHERE day >= :lo AND amount > 0", lo=d7.isoformat()):
        if (u or "").upper() in names:
            goals[kind].add(u.upper())

    games = [{"name": n, "icon": i, "unlocks": c} for n, i, c in _rows(
        session,
        "SELECT m.name, m.icon, COUNT(x.id) FROM minigame m LEFT JOIN userminigameunlock x ON x.minigame_id = m.id "
        "GROUP BY m.id ORDER BY COUNT(x.id) DESC, m.name",
    )]

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "period": period,
        "overview": overview,
        "series": series,
        "per_user": per_user[:200],
        "distribution": distribution,
        "retention": retention,
        "learning": {"last_7d": learning(d7), "last_30d": learning(d30)},
        "daily_goal_users_7d": {k: len(v) for k, v in sorted(goals.items())},
        "minigames": games,
    }
