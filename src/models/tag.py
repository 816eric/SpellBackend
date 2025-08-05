from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


from sqlmodel import Field, SQLModel

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str
    created_by: str  # 'admin' or user id as string
    description: Optional[str] = None


