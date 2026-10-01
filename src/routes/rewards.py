from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlmodel import Session

from src.services.user_manager import UserManager
from src.db_session import get_session_dep
from src.models.user import User
from src.services.reward_service import RewardService, InsufficientPoints
from src.services.chest_service import ChestService

router = APIRouter(prefix="/users", tags=["Rewards"])

DAILY_CLIENT_POINT_CAP = 500

class RedeemRequest(BaseModel):
    item: str = Field(..., min_length=2, max_length=64)
    points: int = Field(..., gt=0)

@router.get("/{name}/points/")
def get_points(name: str, session: Session = Depends(get_session_dep)):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="404: User not found")
    svc = RewardService(session)
    return svc.get_points(name)

class AddPointsRequest(BaseModel):
    # Client-reported earn (FlutterSpell quiz/study). Capped per call and per
    # day so a tampered client can't mint unlimited points.
    points: int = Field(..., gt=0, le=100)
    reason: str = Field(..., min_length=2, max_length=128)

@router.post("/{name}/points/add")
def add_points(name: str, body: AddPointsRequest, session: Session = Depends(get_session_dep)):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = RewardService(session)
    try:
        return svc.add_points(name, body.points, body.reason, daily_cap=DAILY_CLIENT_POINT_CAP)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{name}/points/redeem")
def redeem_points(name: str, body: RedeemRequest, session: Session = Depends(get_session_dep)):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = RewardService(session)
    try:
        return svc.redeem(name, body.item, body.points)
    except InsufficientPoints:
        raise HTTPException(status_code=400, detail="insufficient_points")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{name}/chest")
def get_chest_status(name: str, session: Session = Depends(get_session_dep)):
    """Whether the Home screen's daily treasure chest is still claimable
    today (UTC)."""
    svc = ChestService(session)
    try:
        return svc.status(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{name}/chest/claim")
def claim_chest(name: str, session: Session = Depends(get_session_dep)):
    """Claim today's treasure chest: grants points and marks it claimed
    until the next UTC day."""
    svc = ChestService(session)
    try:
        return svc.claim(name)
    except ValueError as e:
        detail = str(e)
        status_code = 400 if detail == "already_claimed" else 404
        raise HTTPException(status_code=status_code, detail=detail)

@router.get("/{name}/points/history")
def points_history(
    name: str,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_session_dep),
):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = RewardService(session)
    return svc.history_page(name, page)
