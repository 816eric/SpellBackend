from datetime import datetime
from sqlmodel import Session

from src.services.user_manager import UserManager
from src.services.reward_service import RewardService

# Coin payout for opening the Home screen's daily treasure chest.
CHEST_REWARD_POINTS = 20


class ChestService:
    """Home screen's daily treasure chest: one real reward claim per UTC
    day, tracked via User.last_chest_claim_date - same day-string pattern
    MiniGameManager uses for the playtime cap."""

    def __init__(self, session: Session):
        self.session = session

    def _today(self) -> str:
        return datetime.utcnow().date().isoformat()

    def status(self, user_name: str) -> dict:
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        return {"available": user.last_chest_claim_date != self._today()}

    def claim(self, user_name: str) -> dict:
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")

        today = self._today()
        if user.last_chest_claim_date == today:
            raise ValueError("already_claimed")

        user.last_chest_claim_date = today
        self.session.add(user)
        self.session.commit()

        reward = RewardService(self.session).add_points(
            user_name, CHEST_REWARD_POINTS, "Daily treasure chest"
        )
        return {
            "available": False,
            "points_earned": CHEST_REWARD_POINTS,
            "total_points": reward["total_points"],
        }
