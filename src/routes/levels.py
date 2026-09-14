from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db_session import get_session_dep
from src.models.game import Level, LevelProgress
from src.models.user import User
from src.services.level_manager import LevelManager

router = APIRouter(prefix="/levels", tags=["Levels"])


@router.get("/")
def list_levels(session: Session = Depends(get_session_dep)):
    """List all levels."""
    try:
        levels = session.exec(select(Level).order_by(Level.id)).all()
        return [
            {
                "id": level.id,
                "name": level.name,
                "description": level.description,
                "difficulty": level.difficulty,
            }
            for level in levels
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{level_id}")
def get_level(level_id: int, session: Session = Depends(get_session_dep)):
    """Get level details including words."""
    try:
        manager = LevelManager(session)
        level_data = manager.get_level_with_words(level_id)
        if not level_data:
            raise HTTPException(status_code=404, detail="Level not found")
        return level_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_name}/progress/{level_id}/start")
def start_level(
    user_name: str,
    level_id: int,
    session: Session = Depends(get_session_dep)
):
    """Mark level as started."""
    try:
        # Get user by name
        user = session.exec(select(User).where(User.name == user_name)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get or create progress record
        manager = LevelManager(session)
        progress = manager.get_user_level_progress(user.id, level_id)

        # Check if level is unlocked
        if not manager.check_level_unlock(user.id, level_id):
            raise HTTPException(
                status_code=403,
                detail="Level is locked. Complete prerequisite levels first."
            )

        # Mark as started
        if progress.status == "locked":
            progress.status = "in_progress"

        from datetime import datetime
        if not progress.started_at:
            progress.started_at = datetime.utcnow()

        session.add(progress)
        session.commit()

        return {
            "level_id": level_id,
            "user_id": user.id,
            "status": progress.status,
            "message": "Level started"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_name}/progress/{level_id}/complete")
def complete_level(
    user_name: str,
    level_id: int,
    accuracy: float,
    session: Session = Depends(get_session_dep)
):
    """Mark level complete with accuracy score."""
    try:
        # Validate accuracy
        if not (0.0 <= accuracy <= 1.0):
            raise HTTPException(
                status_code=400,
                detail="Accuracy must be between 0.0 and 1.0"
            )

        # Get user by name
        user = session.exec(select(User).where(User.name == user_name)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Complete the level
        manager = LevelManager(session)
        result = manager.complete_level(user.id, level_id, accuracy)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_name}")
def get_user_levels(
    user_name: str,
    session: Session = Depends(get_session_dep)
):
    """Get all levels with user's progress."""
    try:
        # Get user by name
        user = session.exec(select(User).where(User.name == user_name)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all levels with user progress
        manager = LevelManager(session)
        levels = manager.list_user_levels(user.id)

        return {
            "user_name": user_name,
            "levels": levels
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
