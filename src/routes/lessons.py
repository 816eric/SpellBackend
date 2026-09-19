from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from src.models.checkpoint_progress import CheckpointProgress
from src.db_session import get_session
from src.models.user import User
from src.services.lesson_manager import LessonManager

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/{user_name}")
def get_lessons(user_name: str, subject: str, label_type: Optional[str] = None):
    """List grade-filtered lessons for a user, built from the Tag system.

    Groups tags like 'SMSP::P3::EN::Week4' or 'Eric::P3::CN::第一课::read'
    into lessons matching the user's grade and the requested subject
    (EN or CN), with per-lesson word count, mastery, and sequential
    completed/current/locked status computed from the user's passed
    checkpoints and ReviewState. `label_type` (TEACHER, MOE, ...) limits the
    list to that type and computes the sequence within it.
    """
    with get_session() as session:
        user = session.exec(
            select(User).where(User.name == user_name.upper())
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        manager = LessonManager(session)
        lessons = manager.list_lessons_for_user(user, subject, label_type)

        return {
            "user_name": user.name,
            "grade": user.grade,
            "subject": subject.upper(),
            "lessons": lessons,
        }


class CheckpointPassRequest(BaseModel):
    subject: str
    lesson_key: str
    # 0-based checkpoint index, or -1 for the lesson's review node.
    checkpoint_index: int


@router.post("/{user_name}/checkpoint-pass")
def pass_checkpoint(user_name: str, payload: CheckpointPassRequest):
    """Records that the user completed a study session on a checkpoint (or
    a lesson's review node), which is what advances the journey path.
    Idempotent."""
    with get_session() as session:
        user = session.exec(
            select(User).where(User.name == user_name.upper())
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        key = (user.name, payload.subject.upper(), payload.lesson_key, payload.checkpoint_index)
        if not session.get(CheckpointProgress, key):
            session.add(CheckpointProgress(
                user_name=user.name,
                subject=payload.subject.upper(),
                lesson_key=payload.lesson_key,
                checkpoint_index=payload.checkpoint_index,
            ))
            session.commit()
        return {"ok": True}
