from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    password: Optional[str] = ""
    age: Optional[int] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    school: Optional[str] = ""
    grade: Optional[str] = ""
    total_points: int = 0
    #is_admin: bool = False

    # Daily cap on minigame play time (see MiniGameManager). playtime_date
    # is the YYYY-MM-DD (UTC) the seconds counter is for; a mismatch means
    # the counter is stale and should be reset before use.
    playtime_seconds_today: int = 0
    playtime_date: Optional[str] = None

    level_progress: List["LevelProgress"] = Relationship(back_populates="user")
    user_unlockables: List["UserUnlockable"] = Relationship(back_populates="user")