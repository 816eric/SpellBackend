from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db_session import get_session
from src.services.streak_manager import StreakManager
from src.models.user import User
from sqlalchemy import func

router = APIRouter(prefix="/streaks", tags=["streaks"])

def get_user_by_name(user_name: str, session: Session):
    """Helper to get user by name with case-insensitive search."""
    if not user_name:
        return None
    return session.exec(select(User).where(func.upper(User.name) == user_name.upper())).first()

@router.get("/{user_name}")
def get_streak(user_name: str, session: Session = Depends(get_session)):
    """Get user's current streak."""
    user = get_user_by_name(user_name, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    streak = manager.get_user_streak(user.id)
    login_check = manager.check_daily_login(user.id)

    # Convert snake_case to camelCase for frontend compatibility
    return {
        "totalPoints": int(user.total_points) if user.total_points else 0,
        "currentStreak": int(streak.get("current_streak", 0)),
        "lastLogin": streak.get("last_login"),
        "bestStreak": int(streak.get("best_streak", 0)),
        "username": user.name,
        "grade": user.grade if hasattr(user, 'grade') else None,
        "equippedCosmetic": None,
        "levelsCompleted": 0,
        "accuracy": 0.0,
        "level": 1,
        # Keep these for backward compatibility
        "ok": login_check.get("ok", True),
        "message": login_check.get("message", ""),
        "bonusMultiplier": login_check.get("bonus_multiplier", 1.0),
        "milestoneUnlocked": login_check.get("milestone_unlocked", [])
    }

@router.get("/users/{user_name}")
def get_user_streaks(user_name: str, session: Session = Depends(get_session)):
    """Get user's streaks - alias endpoint."""
    user = get_user_by_name(user_name, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    streak = manager.get_user_streak(user.id)
    login_check = manager.check_daily_login(user.id)

    return {
        **streak,
        **login_check
    }

@router.post("/users/{user_name}/check-in")
def check_in_streak(user_name: str, session: Session = Depends(get_session)):
    """Check in to streak - increments daily streak."""
    user = get_user_by_name(user_name, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    result = manager.check_daily_login(user.id)

    return result

@router.post("/{user_name}/revive")
def revive_streak(user_name: str, session: Session = Depends(get_session)):
    """Revive broken streak."""
    user = get_user_by_name(user_name, session)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = StreakManager(session)
    result = manager.revive_streak(user.id)

    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result
