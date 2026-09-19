from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class UserAchievement(SQLModel, table=True):
    """One row per user per achievement ever unlocked - first-unlock-only,
    so re-checking thresholds on every request never re-unlocks (or
    re-times) something already earned."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str = Field(index=True)
    achievement_id: str = Field(index=True)
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)
