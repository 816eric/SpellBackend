from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class Level(SQLModel, table=True):
    """Level definitions for spell progression."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    difficulty: int = Field(ge=1, le=5)
    unlock_requirement: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    words: List["LevelWord"] = Relationship(back_populates="level")
    progress: List["LevelProgress"] = Relationship(back_populates="level")
    challenges: List["Challenge"] = Relationship(back_populates="level")
    statistics: List["LevelStatistics"] = Relationship(back_populates="level")


class LevelWord(SQLModel, table=True):
    """Junction table: words in each level."""
    level_id: int = Field(foreign_key="level.id", primary_key=True)
    word_id: int = Field(foreign_key="spellingword.id", primary_key=True)
    position: int

    level: Optional[Level] = Relationship(back_populates="words")


class LevelProgress(SQLModel, table=True):
    """User progress tracking per level."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    level_id: int = Field(foreign_key="level.id")
    status: str = Field(default="locked")
    stars_earned: int = Field(default=0, ge=0, le=3)
    points_earned: int = Field(default=0)
    study_count: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    level: Optional[Level] = Relationship(back_populates="progress")


class Challenge(SQLModel, table=True):
    """Friend challenges and daily challenges."""
    id: Optional[int] = Field(default=None, primary_key=True)
    challenger_id: int = Field(foreign_key="user.id")
    challengee_id: int = Field(foreign_key="user.id")
    level_id: int = Field(foreign_key="level.id")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    winner_id: Optional[int] = Field(foreign_key="user.id", default=None)
    points_at_stake: int = Field(default=20)

    level: Optional[Level] = Relationship(back_populates="challenges")


class LevelStatistics(SQLModel, table=True):
    """Per-word performance statistics within levels."""
    id: Optional[int] = Field(default=None, primary_key=True)
    level_id: int = Field(foreign_key="level.id")
    word_id: int = Field(foreign_key="spellingword.id")
    total_attempts: int = Field(default=0)
    correct_attempts: int = Field(default=0)
    incorrect_attempts: int = Field(default=0)
    last_attempted_at: Optional[datetime] = None

    level: Optional[Level] = Relationship(back_populates="statistics")
