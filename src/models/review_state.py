from typing import Optional
from datetime import date, datetime
from sqlmodel import SQLModel, Field

class ReviewState(SQLModel, table=True):
    user_name: str = Field(primary_key=True, foreign_key="user.name")
    word_id: int = Field(primary_key=True, foreign_key="spellingword.id")
    repetitions: int = 0
    interval_days: int = 0
    ease_factor: float = 2.5  # SM-2 default
    due_date: Optional[date] = None
    last_reviewed_at: Optional[datetime] = None
    status: Optional[str] = None  # new|learning|review
