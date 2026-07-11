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
    total_points: int = 0
    #is_admin: bool = False

    level_progress: List["LevelProgress"] = Relationship(back_populates="user")