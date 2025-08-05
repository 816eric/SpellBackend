from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    total_points: int = 0
    #is_admin: bool = False