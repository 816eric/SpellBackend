from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class MiniGame(SQLModel, table=True):
    """Catalog entry for a game store title. Either an embeddable
    third-party game (game_type="iframe", html_url set) or a built-in
    Flutter game shipped with the app (game_type="native", native_key
    identifies which screen to launch)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    icon: str = Field(default="🎮")
    game_type: str = Field(default="iframe")  # "iframe" | "native"
    html_url: Optional[str] = None
    native_key: Optional[str] = None
    unlock_cost: int = Field(default=0, ge=0)  # one-time points cost to unlock
    play_cost: int = Field(default=0, ge=0)  # points cost each time it's played
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserMiniGameUnlock(SQLModel, table=True):
    """Tracks which mini-games a user has unlocked (one-time purchase)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    minigame_id: int = Field(foreign_key="minigame.id")
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)
