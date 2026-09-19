from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class BossDefeat(SQLModel, table=True):
    """One row per user per boss ever defeated - first-defeat-only, so a
    boss can't be "defeated" (and rewarded) more than once per user."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str = Field(index=True)
    boss_id: int
    defeated_at: datetime = Field(default_factory=datetime.utcnow)
