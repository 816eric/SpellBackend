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
    # "XP" in the frontend - unified score, never spent/decremented. Still
    # drives the leaderboard ranking and level/achievement thresholds.
    total_points: int = 0
    # Spendable currency, earned in lockstep with total_points (every earn
    # site that increments total_points also increments coins by the same
    # amount) and decremented by minigame unlocks/plays, streak revives, and
    # cosmetic redemptions. Backfilled from total_points for existing users
    # the one time this column was added - see database/init_db.py.
    coins: int = 0
    # Bonus currency, not spent anywhere yet. Granted only as a small extra
    # on top of existing rewards: boss victories and achievement unlocks.
    gems: int = 0
    #is_admin: bool = False

    # Daily cap on minigame play time (see MiniGameManager). playtime_date
    # is the YYYY-MM-DD (UTC) the seconds counter is for; a mismatch means
    # the counter is stale and should be reset before use.
    playtime_seconds_today: int = 0
    playtime_date: Optional[str] = None

    # YYYY-MM-DD (UTC) the daily treasure chest was last claimed - a
    # mismatch with today's date means it's available again.
    last_chest_claim_date: Optional[str] = None

    level_progress: List["LevelProgress"] = Relationship(back_populates="user")
    user_unlockables: List["UserUnlockable"] = Relationship(back_populates="user")