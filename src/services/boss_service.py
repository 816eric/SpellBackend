from typing import List
from sqlmodel import Session, select

from src.services.user_manager import UserManager
from src.services.reward_service import RewardService
from src.models.boss import BossDefeat

# Boss Arena's per-boss XP reward (mirrors the Flutter mock's boss data in
# boss_battle_screen.dart - kept here since this is now the source of truth
# for what actually gets credited to the user's points).
BOSS_REWARD_POINTS = {1: 100, 2: 200, 3: 300}


class BossService:
    def __init__(self, session: Session):
        self.session = session

    def defeated_boss_ids(self, user_name: str) -> List[int]:
        rows = self.session.exec(
            select(BossDefeat.boss_id).where(BossDefeat.user_name == user_name)
        ).all()
        return sorted(rows)

    def defeat(self, user_name: str, boss_id: int) -> dict:
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")

        existing = self.session.exec(
            select(BossDefeat).where(
                BossDefeat.user_name == user_name,
                BossDefeat.boss_id == boss_id,
            )
        ).first()
        if existing:
            return {
                "first_time": False,
                "points_earned": 0,
                "total_points": user.total_points or 0,
            }

        self.session.add(BossDefeat(user_name=user_name, boss_id=boss_id))
        self.session.commit()

        points = BOSS_REWARD_POINTS.get(boss_id, 0)
        total_points = user.total_points or 0
        if points > 0:
            reward = RewardService(self.session).add_points(
                user_name, points, f"Defeated boss {boss_id}"
            )
            total_points = reward["total_points"]

        return {
            "first_time": True,
            "points_earned": points,
            "total_points": total_points,
        }
