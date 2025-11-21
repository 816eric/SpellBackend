from typing import Optional
from sqlmodel import SQLModel, Field

class UserTagsLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tag_id: int = Field(foreign_key="tag.id")

class WordTagLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="spellingword.id")
    tag_id: int = Field(foreign_key="tag.id")
