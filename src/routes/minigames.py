from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db_session import get_session
from src.services.minigame_manager import MiniGameManager
from src.models.user import User

router = APIRouter(prefix="/minigames", tags=["minigames"])


def _get_user(user_name: str, session: Session) -> User:
    user = session.exec(select(User).where(User.name == user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/")
def list_minigames(user_name: str, session: Session = Depends(get_session)):
    """List the game store catalog with this user's unlock status and coin balance."""
    user = _get_user(user_name, session)
    manager = MiniGameManager(session)
    return manager.get_user_minigames(user.id)


@router.post("/{minigame_id}/unlock")
def unlock_minigame(user_name: str, minigame_id: int, session: Session = Depends(get_session)):
    """Spend coins to permanently unlock a game."""
    user = _get_user(user_name, session)
    manager = MiniGameManager(session)
    result = manager.unlock_minigame(user.id, minigame_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/{minigame_id}/play")
def play_minigame(user_name: str, minigame_id: int, session: Session = Depends(get_session)):
    """Spend the per-play cost and get back the game's embeddable URL."""
    user = _get_user(user_name, session)
    manager = MiniGameManager(session)
    result = manager.play_minigame(user.id, minigame_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result
