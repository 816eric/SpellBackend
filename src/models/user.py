from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    name: str = Field(primary_key=True)
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    total_points: int = 0
    #is_admin: bool = False