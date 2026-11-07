from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.db_session import get_session_dep
from src.services.report_service import build_child_report

router = APIRouter(prefix="/users", tags=["report"])


@router.get("/{name}/report")
def child_report(name: str, session: Session = Depends(get_session_dep)):
    """Progress summary for the parent view. AuthMiddleware already limits
    /users/{name}/... to that user's own token."""
    return build_child_report(session, name)
