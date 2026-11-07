from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.db_session import get_session_dep
from src.models.usage import UsageDay

router = APIRouter(prefix="/usage", tags=["usage"])

# The app reports roughly every 30s; allow slack for slow timers but not
# enough to let a client invent hours of use in one call.
MAX_SECONDS_PER_CALL = 120
MAX_SECONDS_PER_DAY = 16 * 3600


class Heartbeat(BaseModel):
    seconds: int = Field(ge=0, le=MAX_SECONDS_PER_CALL)


@router.post("/heartbeat")
def heartbeat(body: Heartbeat, request: Request, session: Session = Depends(get_session_dep)):
    """Add `seconds` of foreground time to the signed-in user's total for today."""
    name = getattr(request.state, "user_name", None)
    if not name:
        raise HTTPException(status_code=401, detail="Authentication required")
    day = datetime.utcnow().strftime("%Y-%m-%d")
    row = session.get(UsageDay, (name.upper(), day))
    if row is None:
        row = UsageDay(user_name=name.upper(), day=day, seconds=0)
    row.seconds = min(row.seconds + body.seconds, MAX_SECONDS_PER_DAY)
    session.add(row)
    session.commit()
    return {"ok": True}
