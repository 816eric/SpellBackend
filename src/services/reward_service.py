from typing import Dict, Any, List, Tuple
from datetime import datetime
from sqlmodel import Session, select, desc, func

from src.services.user_manager import UserManager
from src.models.user import User
from src.models.reward import RewardHistory

PAGE_SIZE = 20

class InsufficientPoints(Exception):
    pass

class RewardService:
    def __init__(self, session: Session):
        self.session = session

    def get_points(self, user_name: str) -> Dict[str, Any]:
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        # Optionally preview latest 5 history items
        preview = self.session.exec(
            select(RewardHistory)
            .where(RewardHistory.user_name == user_name)
            .order_by(desc(RewardHistory.timestamp))
            .limit(5)
        ).all()
        return {
            "total_points": user.total_points or 0,
            "history_preview": [
                {
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    "action": h.action,
                    "points": h.points,
                    "reason": h.reason,
                }
                for h in preview
            ],
        }

    def add_points(self, user_name: str, points: int, reason: str) -> Dict[str, Any]:
        """Add points to user account"""
        if points <= 0:
            raise ValueError("points must be positive")
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        # add points & create history
        user.total_points = (user.total_points or 0) + points
        now = datetime.now()
        hist = RewardHistory(
            user_name=user_name,
            action="earn",
            points=points,
            reason=reason,
            timestamp=now,
        )
        self.session.add(hist)
        self.session.commit()
        return {"ok": True, "total_points": user.total_points, "points_earned": points}

    def redeem(self, user_name: str, item: str, points: int) -> Dict[str, Any]:
        if points <= 0:
            raise ValueError("points must be positive")
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        if (user.total_points or 0) < points:
            raise InsufficientPoints("insufficient_points")
        # deduct & create history
        user.total_points = (user.total_points or 0) - points
        now = datetime.now()
        hist = RewardHistory(
            user_name=user_name,
            action="redeem",
            points=-points,
            reason=item,
            timestamp=now,
        )
        self.session.add(hist)
        # Optional: update last_point_earned_at for tie-breaker — for redeem we leave it as is
        self.session.commit()
        return {"ok": True, "total_points": user.total_points}

    def history_page(self, user_name: str, page: int) -> Dict[str, Any]:
        if page < 1:
            page = 1
        # total count
        total = self.session.exec(
            select(func.count()).select_from(
                select(RewardHistory)
                .where(RewardHistory.user_name == user_name)
                .subquery()
            )
        ).one()
        # items
        offset = (page - 1) * PAGE_SIZE
        items = self.session.exec(
            select(RewardHistory)
            .where(RewardHistory.user_name == user_name)
            .order_by(desc(RewardHistory.timestamp))
            .limit(PAGE_SIZE)
            .offset(offset)
        ).all()
        return {
            "page": page,
            "size": PAGE_SIZE,
            "total": total,
            "items": [
                {
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    "action": h.action,
                    "points": h.points,
                    "reason": h.reason,
                }
                for h in items
            ],
        }
