from sqlmodel import Session, select
from src.models.user import User
from src.models.reward import RewardHistory
from datetime import datetime

class RewardSystem:
    def __init__(self, session: Session):
        self.session = session

    def get_points_and_history(self, user_name: str):
        user = self.session.get(User, user_name)
        history = self.session.exec(select(RewardHistory).where(RewardHistory.user_name == user_name)).all()
        return {"points": user.total_points, "history": history}

    def redeem_points(self, user_name: str, points: int, reason: str):
        user = self.session.get(User, user_name)
        if user.total_points < points:
            raise ValueError("Not enough points")

        user.total_points -= points
        history = RewardHistory(
            user_name=user_name,
            action="redeem",
            points=points,
            reason=reason,
            timestamp=datetime.now()
        )
        self.session.add(history)
        self.session.commit()
        return history