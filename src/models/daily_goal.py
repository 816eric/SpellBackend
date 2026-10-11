from sqlmodel import SQLModel, Field
from typing import Optional


class DailyActivity(SQLModel, table=True):
    """Per-user, per-day progress counter for one daily-goal kind
    (see DailyGoalService). `day` is YYYY-MM-DD (UTC), like the playtime
    counter on User."""
    user_name: str = Field(primary_key=True)
    day: str = Field(primary_key=True)
    kind: str = Field(primary_key=True)  # "words" | "stage" | "math"
    amount: int = 0
