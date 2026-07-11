from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Level(SQLModel, table=True):
    """Represents a spelling level in the game"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    difficulty: int = Field(default=1)  # 1-10 scale
    order: int = Field(default=1)  # Display order
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LevelProgress(SQLModel, table=True):
    """Tracks user progress through a level"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str = Field(foreign_key="user.name", index=True)
    level_id: int = Field(foreign_key="level.id", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = Field(default="in_progress")  # in_progress, completed, abandoned
    words_mastered: int = Field(default=0)
    attempts: int = Field(default=0)
    score: int = Field(default=0)


class LevelWord(SQLModel, table=True):
    """Associates words with levels"""
    id: Optional[int] = Field(default=None, primary_key=True)
    level_id: int = Field(foreign_key="level.id", index=True)
    word_id: int = Field(foreign_key="spellingword.id", index=True)
    word_order: int = Field(default=0)  # Order of word in level
    difficulty_modifier: float = Field(default=1.0)  # Multiplier for level's difficulty
