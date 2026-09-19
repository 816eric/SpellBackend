from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from src.db_session import get_session_dep
from src.services.boss_service import BossService

router = APIRouter(prefix="/users", tags=["Bosses"])


@router.get("/{name}/bosses")
def get_defeated_bosses(name: str, session: Session = Depends(get_session_dep)):
    """Boss ids this user has ever defeated (Boss Arena)."""
    svc = BossService(session)
    return {"defeated": svc.defeated_boss_ids(name)}


@router.post("/{name}/bosses/{boss_id}/defeat")
def defeat_boss(name: str, boss_id: int, session: Session = Depends(get_session_dep)):
    """Records a boss win. Idempotent per boss - only the first defeat
    grants points; repeats just report first_time=False."""
    svc = BossService(session)
    try:
        return svc.defeat(name, boss_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
