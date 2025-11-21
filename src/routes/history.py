from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import datetime
from src.db_session import get_session
from src.models.history import StudySessionHistory, QuizSessionHistory

router = APIRouter(prefix="/history", tags=["History"])

class StudyRecord(BaseModel):
    word: str
    difficulty: int  # 0=Again, 1=Hard, 3=Good, 5=Easy

class StudySessionRequest(BaseModel):
    user_name: str
    records: List[StudyRecord]

class QuizRecord(BaseModel):
    word: str
    is_correct: bool

class QuizSessionRequest(BaseModel):
    user_name: str
    records: List[QuizRecord]

@router.post("/study-session")
def save_study_session(data: StudySessionRequest):
    """Save a batch of study records from a study session"""
    with get_session() as session:
        timestamp = datetime.utcnow()
        for record in data.records:
            history = StudySessionHistory(
                user_name=data.user_name,
                word=record.word,
                difficulty=record.difficulty,
                studied_at=timestamp
            )
            session.add(history)
        session.commit()
        return {
            "success": True, 
            "message": f"Saved {len(data.records)} study records",
            "count": len(data.records)
        }

@router.post("/quiz-session")
def save_quiz_session(data: QuizSessionRequest):
    """Save a batch of quiz records from a quiz session"""
    with get_session() as session:
        timestamp = datetime.utcnow()
        for record in data.records:
            history = QuizSessionHistory(
                user_name=data.user_name,
                word=record.word,
                is_correct=record.is_correct,
                completed_at=timestamp
            )
            session.add(history)
        session.commit()
        correct_count = sum(1 for r in data.records if r.is_correct)
        return {
            "success": True,
            "message": f"Saved {len(data.records)} quiz records",
            "total": len(data.records),
            "correct": correct_count,
            "accuracy": correct_count / len(data.records) if data.records else 0
        }

@router.get("/study/{user_name}")
def get_study_history(user_name: str, limit: int = 100):
    """Get recent study session history for a user"""
    with get_session() as session:
        records = session.query(StudySessionHistory).filter(
            StudySessionHistory.user_name == user_name
        ).order_by(StudySessionHistory.studied_at.desc()).limit(limit).all()
        return [
            {
                "word": r.word,
                "difficulty": r.difficulty,
                "studied_at": r.studied_at.isoformat()
            }
            for r in records
        ]

@router.get("/quiz/{user_name}")
def get_quiz_history(user_name: str, limit: int = 100):
    """Get recent quiz session history for a user"""
    with get_session() as session:
        records = session.query(QuizSessionHistory).filter(
            QuizSessionHistory.user_name == user_name
        ).order_by(QuizSessionHistory.completed_at.desc()).limit(limit).all()
        return [
            {
                "word": r.word,
                "is_correct": r.is_correct,
                "completed_at": r.completed_at.isoformat()
            }
            for r in records
        ]

@router.delete("/study/{user_name}")
def clear_study_history(user_name: str):
    """Delete all study history for a user"""
    with get_session() as session:
        count = session.query(StudySessionHistory).filter(
            StudySessionHistory.user_name == user_name
        ).delete()
        session.commit()
        return {
            "success": True,
            "message": f"Deleted {count} study records",
            "count": count
        }

@router.delete("/quiz/{user_name}")
def clear_quiz_history(user_name: str):
    """Delete all quiz history for a user"""
    with get_session() as session:
        count = session.query(QuizSessionHistory).filter(
            QuizSessionHistory.user_name == user_name
        ).delete()
        session.commit()
        return {
            "success": True,
            "message": f"Deleted {count} quiz records",
            "count": count
        }
