from datetime import datetime
from sqlmodel import SQLModel, Field


class CheckpointProgress(SQLModel, table=True):
    """A checkpoint (or, with checkpoint_index == -1, a lesson's review
    node) the user has passed by completing a study session on it. Kept
    separately from ReviewState so progress along the journey path doesn't
    regress when a later spaced review of one of its words is missed."""
    user_name: str = Field(primary_key=True, foreign_key="user.name")
    subject: str = Field(primary_key=True)  # 'EN' | 'CN'
    lesson_key: str = Field(primary_key=True)
    checkpoint_index: int = Field(primary_key=True)
    passed_at: datetime = Field(default_factory=datetime.now)
