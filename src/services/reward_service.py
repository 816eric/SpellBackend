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
            "coins": user.coins or 0,
            "gems": user.gems or 0,
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

    def add_points(self, user_name: str, points: int, reason: str, daily_cap: int = None) -> Dict[str, Any]:
        """Add points to user account. `daily_cap` limits how many points
        this user may have earned today (all earn sources) via this call."""
        if points <= 0:
            raise ValueError("points must be positive")
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        if daily_cap is not None:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            earned = self.session.exec(
                select(func.coalesce(func.sum(RewardHistory.points), 0)).where(
                    RewardHistory.user_name == user_name,
                    RewardHistory.action == "earn",
                    RewardHistory.timestamp >= start,
                )
            ).one()
            if earned + points > daily_cap:
                raise ValueError("daily point limit reached")
        # add points & create history. coins is spendable currency and is
        # earned in lockstep with XP (total_points) everywhere the latter
        # increases - see the coins/gems design notes on User.
        user.total_points = (user.total_points or 0) + points
        user.coins = (user.coins or 0) + points
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
        return {
            "ok": True,
            "total_points": user.total_points,
            "coins": user.coins,
            "points_earned": points,
        }

    def redeem(self, user_name: str, item: str, points: int) -> Dict[str, Any]:
        """Spend coins (not XP - XP is never decremented) for a generic
        item. Note: unused by the current Flutter frontend, but kept
        consistent with the other coin-spend gates (minigames, streak
        revive, cosmetics)."""
        if points <= 0:
            raise ValueError("points must be positive")
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")
        if (user.coins or 0) < points:
            raise InsufficientPoints("insufficient_points")
        # deduct & create history
        user.coins = (user.coins or 0) - points
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
        return {"ok": True, "coins": user.coins}

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
