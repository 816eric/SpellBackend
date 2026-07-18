from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


from sqlmodel import Field, SQLModel

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str
    created_by: str  # 'admin' or user id as string
    description: Optional[str] = None
    # Source of this label: "TEACHER" (default, created by a teacher/school
    # account) or "MOE" (centrally-curated official curriculum content).
    label_type: Optional[str] = Field(default="TEACHER")
    # Free-text date this lesson/dictation is scheduled for, e.g. "七月十四日".
    # Stored as raw text (not a real date) since source data often omits the
    # year and uses Chinese numerals. Populated from JSON import when
    # available; otherwise left empty for a teacher/admin to fill in later.
    spell_date: Optional[str] = None


