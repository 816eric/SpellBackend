from sqlmodel import SQLModel, Field
from typing import Optional

class UserSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    study_words_source: str = Field(default="ALL_TAGS")  # "ALL_TAGS" or "CURRENT_TAG"
    num_study_words: int = Field(default=10)
    spell_repeat_count: int = Field(default=1, description="Number of times a word must be spelled correctly to be considered mastered.")
