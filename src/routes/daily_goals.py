from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from src.db_session import get_session_dep
from src.models.user import User
from src.services import daily_goal_service as svc

router = APIRouter(prefix="/daily-goals", tags=["daily-goals"])


def _get_user(user_name: str, session: Session) -> User:
    user = session.exec(select(User).where(func.upper(User.name) == user_name.upper())).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/")
def get_daily_goals(user_name: str, session: Session = Depends(get_session_dep)):
    """Today's goals with progress, and whether all are complete (which
    unlocks the game store)."""
    user = _get_user(user_name, session)
    return svc.get_status(session, user.name)


@router.post("/moe-session")
def complete_moe_session(user_name: str, session: Session = Depends(get_session_dep)):
    """Client reports a finished MOE word-cards session."""
    user = _get_user(user_name, session)
    svc.record_activity(session, user.name, "moe")
    return svc.get_status(session, user.name)


@router.post("/math-time")
def report_math_time(user_name: str, seconds: int, session: Session = Depends(get_session_dep)):
    """Heartbeat from the client while AI Math (an embedded external app)
    is open, reporting elapsed seconds toward the AI Math goal."""
    user = _get_user(user_name, session)
    svc.record_activity(session, user.name, "math", max(0, min(seconds, 60)))
    return svc.get_status(session, user.name)


@router.post("/practice")
def complete_practice(user_name: str, subject: str, session: Session = Depends(get_session_dep)):
    """Client reports a finished free-practice session (a completed lesson,
    which doesn't pass a checkpoint) toward the English/Chinese stage goal."""
    user = _get_user(user_name, session)
    kind = {"EN": "english", "CN": "chinese"}.get(subject.upper())
    if not kind:
        raise HTTPException(status_code=400, detail="Unknown subject")
    svc.record_activity(session, user.name, kind)
    return svc.get_status(session, user.name)
