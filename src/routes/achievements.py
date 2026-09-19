from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from src.db_session import get_session_dep
from src.services.achievement_service import AchievementService

router = APIRouter(prefix="/users", tags=["Achievements"])


@router.get("/{name}/achievements")
def get_achievements(name: str, session: Session = Depends(get_session_dep)):
    """Every achievement's unlock state, checking+persisting any
    newly-crossed threshold as a side effect (see AchievementService)."""
    svc = AchievementService(session)
    try:
        return {"achievements": svc.list_for_user(name)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
