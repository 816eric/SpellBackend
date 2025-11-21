from sqlmodel import SQLModel, Field
from typing import List, Optional

class SpellingWord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    language: Optional[str] = Field(default="other")
    created_by: Optional[str] = Field(default="admin")
    back_card: Optional[str] = Field(default=None)