from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.db_session import get_session
from src.services.streak_manager import StreakManager

router = APIRouter(prefix="/streaks", tags=["streaks"])

@router.get("/{user_name}")
def get_streak(user_name: str, session: Session = Depends(get_session)):
    """Get user's current streak."""
    from src.models.user import User

    user = session.exec("SELECT * FROM user WHERE name = ?", [user_name]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    streak = manager.get_user_streak(user.id)
    login_check = manager.check_daily_login(user.id)

    return {
        **streak,
        **login_check
    }

@router.post("/{user_name}/revive")
def revive_streak(user_name: str, session: Session = Depends(get_session)):
    """Revive broken streak."""
    from src.models.user import User

    user = session.exec("SELECT * FROM user WHERE name = ?", [user_name]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    result = manager.revive_streak(user.id)

    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result
