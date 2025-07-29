from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class StudyHistory(SQLModel, table=True):
    user_name: str = Field(foreign_key="user.name", primary_key=True)
    word_id: int = Field(foreign_key="spellingword.id", primary_key=True)
    count: int = 0
    last_studied_at: Optional[datetime] = None

class LoginHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    timestamp: datetime
    tag: Optional[str] = None