from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class RewardHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    action: str  # 'earn' or 'redeem'
    points: int
    reason: Optional[str] = None
    timestamp: datetime