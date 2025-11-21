from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlmodel import Session

from src.services.user_manager import UserManager
from src.db_session import get_session
from src.models.user import User
from src.services.reward_service import RewardService, InsufficientPoints

router = APIRouter(prefix="/users", tags=["Rewards"])

class RedeemRequest(BaseModel):
    item: str = Field(..., min_length=2, max_length=64)
    points: int = Field(..., gt=0)

@router.get("/{name}/points/")
def get_points(name: str, session: Session = Depends(get_session)):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="404: User not found")
    svc = RewardService(session)
    return svc.get_points(name)

class AddPointsRequest(BaseModel):
    points: int = Field(..., gt=0)
    reason: str = Field(..., min_length=2, max_length=128)

@router.post("/{name}/points/add")
def add_points(name: str, body: AddPointsRequest, session: Session = Depends(get_session)):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = RewardService(session)
    try:
        return svc.add_points(name, body.points, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{name}/points/redeem")
def redeem_points(name: str, body: RedeemRequest, session: Session = Depends(get_session)):
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

@router.get("/{name}/points/history")
def points_history(
    name: str,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_session),
):
    manager = UserManager(session)
    user = manager.get_user(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = RewardService(session)
    return svc.history_page(name, page)
