from datetime import datetime
from sqlalchemy import func
from sqlmodel import Session, select
from src.models.user import User
from src.models.daily_goal import DailyActivity

# Fixed daily goals. Only `required` ones gate the game store. `target` is in `unit`s; math is tracked in seconds.
# Stage goals are recorded by checkpoint-pass (by subject); the MOE session
# goal by the client when a word-cards session is finished.
DAILY_GOALS = [
    {"kind": "english", "title": "English spelling stage", "icon": "🏰", "target": 1, "unit": "stage", "required": True},
    {"kind": "chinese", "title": "Chinese spelling stage", "icon": "🐉", "target": 1, "unit": "stage", "required": True},
    {"kind": "moe", "title": "Chinese word cards session", "icon": "🈶", "target": 1, "unit": "session", "required": True},
    {"kind": "math", "title": "AI Math", "icon": "🔢", "target": 10 * 60, "unit": "seconds", "required": False},
]
# Not goals: `practice` accumulates seconds spent in spelling study sessions;
# `practice_base` is the practice total at the moment the first round was
# completed (the first 10 minutes of game time cover that practice).
_KINDS = {g["kind"] for g in DAILY_GOALS} | {"practice"}
_REQUIRED = [g for g in DAILY_GOALS if g["required"]]


def _today() -> str:
    return datetime.utcnow().date().isoformat()


def record_activity(session: Session, user_name: str, kind: str, amount: int = 1) -> None:
    """Add `amount` to today's counter for `kind`. Caller's session is
    committed here."""
    if kind not in _KINDS or amount <= 0:
        return
    key = (user_name, _today(), kind)
    row = session.get(DailyActivity, key)
    if row:
        row.amount += amount
    else:
        row = DailyActivity(user_name=key[0], day=key[1], kind=kind, amount=amount)
    session.add(row)
    session.commit()
    if kind != "practice":
        _snapshot_practice_base(session, user_name)


def _amount(session: Session, user_name: str, kind: str):
    row = session.get(DailyActivity, (user_name, _today(), kind))
    return row.amount if row else None


def _snapshot_practice_base(session: Session, user_name: str) -> None:
    """When the required goals are first all met today, remember how much
    practice time had been logged by then: that practice paid for the first
    10 minutes of game time, so only practice after this point earns more."""
    if _amount(session, user_name, "practice_base") is not None:
        return
    if all((_amount(session, user_name, g["kind"]) or 0) >= g["target"] for g in _REQUIRED):
        session.add(DailyActivity(
            user_name=user_name, day=_today(), kind="practice_base",
            amount=_amount(session, user_name, "practice") or 0,
        ))
        session.commit()


# Completing the required goals the first time earns 10 minutes of game time.
# Every further full pass ("round") earns game time equal to the spelling
# practice time since the previous one, but always under 10 minutes.
PLAYTIME_BLOCK_SECONDS = 10 * 60
MAX_EXTRA_PER_ROUND_SECONDS = PLAYTIME_BLOCK_SECONDS - 1
# Test accounts (User.is_tester) are never gated or capped.
TESTER_PLAYTIME_SECONDS = 24 * 60 * 60


def _is_tester(session: Session, user_name: str) -> bool:
    user = session.exec(
        select(User).where(func.upper(User.name) == user_name.upper())
    ).first()
    return bool(user and user.is_tester)


def get_status(session: Session, user_name: str) -> dict:
    """Required-goal counters keep accumulating past the target, so each
    full pass over them is a "round". The returned goals show progress for
    the current round, which starts fresh when the previous one completes.
    `playtimeLimitSeconds` is the day's total game-time allowance."""
    today = _today()
    amounts = {}
    for g in DAILY_GOALS:
        row = session.get(DailyActivity, (user_name, today, g["kind"]))
        amounts[g["kind"]] = row.amount if row else 0

    rounds = min(amounts[g["kind"]] // g["target"] for g in DAILY_GOALS if g["required"])
    goals = []
    for g in DAILY_GOALS:
        amount = amounts[g["kind"]]
        if g["required"]:
            amount -= rounds * g["target"]
        progress = max(0, min(amount, g["target"]))
        goals.append({**g, "progress": progress, "done": progress >= g["target"]})

    tester = _is_tester(session, user_name)
    limit = 0
    if rounds >= 1:
        practice = _amount(session, user_name, "practice") or 0
        base = _amount(session, user_name, "practice_base")
        if base is None:  # day predates tracking: no practice credit
            base = practice
        extra = min(max(0, practice - base), (rounds - 1) * MAX_EXTRA_PER_ROUND_SECONDS)
        limit = PLAYTIME_BLOCK_SECONDS + extra
    return {
        "goals": goals,
        "rounds": rounds,
        "allDone": tester or rounds >= 1,
        "playtimeLimitSeconds": TESTER_PLAYTIME_SECONDS if tester else limit,
    }
