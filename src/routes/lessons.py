from fastapi import APIRouter, HTTPException
from sqlmodel import select
from src.db_session import get_session
from src.models.user import User
from src.services.lesson_manager import LessonManager

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/{user_name}")
def get_lessons(user_name: str, subject: str):
    """List grade-filtered lessons for a user, built from the Tag system.

    Groups tags like 'SJIJ::P3::EN::Week4' or 'Eric::P3::CN::第一课::read'
    into lessons matching the user's grade and the requested subject
    (EN or CN), with per-lesson word count, mastery, and sequential
    completed/current/locked status computed from ReviewState.
    """
    with get_session() as session:
        user = session.exec(
            select(User).where(User.name == user_name.upper())
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        manager = LessonManager(session)
        lessons = manager.list_lessons_for_user(user, subject)

        return {
            "user_name": user.name,
            "grade": user.grade,
            "subject": subject.upper(),
            "lessons": lessons,
        }
