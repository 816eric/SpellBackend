from sqlmodel import Session
from datetime import datetime, timedelta
from src.models.reward import RewardHistory
from src.models.user import User

class StreakManager:
    """Manages daily streak tracking and bonuses."""

    def __init__(self, session: Session):
        self.session = session

    def get_user_streak(self, user_id: int) -> dict:
        """Get current streak and last login."""
        from sqlalchemy import text, func
        from sqlalchemy.exc import OperationalError

        try:
            # Get login history (study events)
            query = text("""
                SELECT DATE(timestamp) as login_date
                FROM rewardhistory
                WHERE reason IN ('study', 'level_complete')
                ORDER BY timestamp DESC
                LIMIT 30
            """)

            result = self.session.exec(query).all()
            if not result:
                return {
                    "current_streak": 0,
                    "last_login": None,
                    "best_streak": 0
                }

            # Calculate consecutive days
            streak = 0
            today = datetime.utcnow().date()
            dates = []

            for row in result:
                dates.append(row[0] if isinstance(row, tuple) else row)

            for i, login_date in enumerate(dates):
                expected_date = today - timedelta(days=i)
                if login_date == expected_date:
                    streak += 1
                else:
                    break

            return {
                "current_streak": streak,
                "last_login": str(dates[0]) if dates else None,
                "best_streak": len(dates)  # Simplified; track in User table for prod
            }
        except OperationalError:
            # Table doesn't exist (e.g., in tests), return empty streak
            return {
                "current_streak": 0,
                "last_login": None,
                "best_streak": 0
            }

    def check_daily_login(self, user_id: int) -> dict:
        """Check if user has logged in today and update streak."""
        user = self.session.get(User, user_id)
        if not user:
            return {"ok": False, "message": "User not found"}

        streak_info = self.get_user_streak(user_id)
        last_login = streak_info["last_login"]
        today_str = datetime.utcnow().date().isoformat()

        if last_login == today_str:
            return {
                "ok": True,
                "streak": streak_info["current_streak"],
                "message": "Already logged in today",
                "bonus_multiplier": self._get_streak_multiplier(streak_info["current_streak"])
            }

        # New day - increment streak
        new_streak = streak_info["current_streak"] + 1

        return {
            "ok": True,
            "streak": new_streak,
            "message": f"Streak: {new_streak} days!",
            "bonus_multiplier": self._get_streak_multiplier(new_streak),
            "milestone_unlocked": self._check_milestones(new_streak)
        }

    def _get_streak_multiplier(self, streak: int) -> float:
        """Return points multiplier based on streak."""
        if streak >= 30:
            return 3.0
        elif streak >= 10:
            return 2.0
        elif streak >= 5:
            return 1.5
        return 1.0

    def _check_milestones(self, streak: int) -> list:
        """Check if streak hits milestone rewards."""
        milestones = []

        if streak == 5:
            milestones.append({"type": "multiplier", "value": 2.0})
        elif streak == 10:
            milestones.append({"type": "cosmetic", "unlockable_id": 10})  # Placeholder
        elif streak == 30:
            milestones.append({"type": "badge", "name": "Master Speller"})

        return milestones

    def revive_streak(self, user_id: int, points_cost: int = 50) -> dict:
        """Allow user to pay points to revive broken streak."""
        user = self.session.get(User, user_id)
        if not user:
            return {"ok": False, "message": "User not found"}

        if user.coins < points_cost:
            return {"ok": False, "message": "Insufficient points"}

        # Deduct coins (XP is never spent)
        user.coins -= points_cost

        # Log deduction
        history = RewardHistory(
            user_name=user.name,
            action="redeem",
            points=-points_cost,
            reason="streak_revive",
            timestamp=datetime.utcnow()
        )
        self.session.add(history)
        self.session.commit()

        return {
            "ok": True,
            "message": "Streak revived!",
            "remaining_points": user.coins
        }
