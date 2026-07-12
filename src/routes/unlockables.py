from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db_session import get_session
from src.services.unlockable_manager import UnlockableManager
from src.models.user import User

router = APIRouter(prefix="/unlockables", tags=["unlockables"])

@router.get("/")
def list_unlockables(user_name: str, session: Session = Depends(get_session)):
    """List all unlockables with ownership status."""
    user = session.exec(select(User).where(User.name == user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = UnlockableManager(session)
    return manager.get_user_unlockables(user.id)

@router.post("/{unlockable_id}/redeem")
def redeem_unlockable(user_name: str, unlockable_id: int, session: Session = Depends(get_session)):
    """Redeem points for a cosmetic."""
    user = session.exec(select(User).where(User.name == user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = UnlockableManager(session)
    result = manager.redeem_unlockable(user.id, unlockable_id)

    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.post("/{unlockable_id}/equip")
def equip_cosmetic(user_name: str, unlockable_id: int, session: Session = Depends(get_session)):
    """Equip a cosmetic."""
    user = session.exec(select(User).where(User.name == user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager = UnlockableManager(session)
    result = manager.equip_cosmetic(user.id, unlockable_id)

    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result
