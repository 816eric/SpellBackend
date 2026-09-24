from sqlmodel import SQLModel, Field
from typing import List, Optional

class SpellingWord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    language: Optional[str] = Field(default="other")
    created_by: Optional[str] = Field(default="admin")
    back_card: Optional[str] = Field(default=None)
    quiz: Optional[str] = Field(default=None)
    # Hanyu Pinyin with tone marks (e.g. "yī"), and a short English gloss.
    # Used by the MOE Chinese Word Cards flip-card feature; left null for
    # words that predate/don't need this (e.g. English words).
    pinyin: Optional[str] = Field(default=None)
    meaning: Optional[str] = Field(default=None)