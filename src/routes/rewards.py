from fastapi import APIRouter
from src.db_session import get_session
from src.services.reward_system import RewardSystem

router = APIRouter(prefix="/users", tags=["Rewards"])

@router.get("/{name}/points/")
def get_points(name: str):
    with get_session() as session:
        reward = RewardSystem(session)
        return reward.get_points_and_history(name)

@router.post("/{name}/points/redeem")
def redeem_points(name: str, points: int, reason: str = "redeem"):
    with get_session() as session:
        reward = RewardSystem(session)
        return reward.redeem_points(name, points, reason)