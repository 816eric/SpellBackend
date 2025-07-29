from fastapi import APIRouter
from src.db_session import get_session
from src.services.study_tracker import StudyTracker

router = APIRouter(prefix="/users", tags=["Study"])

@router.post("/{name}/study/")
def log_study(name: str, word_id: int):
    with get_session() as session:
        tracker = StudyTracker(session)
        return tracker.log_study(name, word_id)