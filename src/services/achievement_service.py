from typing import Any, Dict, List
from sqlalchemy import func
from sqlmodel import Session, select

from src.services.user_manager import UserManager
from src.services.streak_manager import StreakManager
from src.services.boss_service import BossService
from src.models.game import LevelProgress
from src.models.achievement import UserAchievement

# Static achievement definitions. Each "check" runs against the stats dict
# built by _gather_stats below. Ordered to match the milestone list the
# Progress screen used to hardcode.
ACHIEVEMENTS = [
    {
        "id": "stage_1_complete",
        "icon": "🏁",
        "label": "Stage 1 Complete (Vowels)",
        "check": lambda s: s["levels_completed"] >= 1,
    },
    {
        "id": "stage_5_complete",
        "icon": "🏁",
        "label": "Stage 5 Complete (Review)",
        "check": lambda s: s["levels_completed"] >= 5,
    },
    {
        "id": "boss_1_defeated",
        "icon": "🏁",
        "label": "Boss 1 Defeated",
        "check": lambda s: 1 in s["defeated_boss_ids"],
    },
    {
        "id": "streak_7",
        "icon": "🏁",
        "label": "7-Day Streak Achieved",
        "check": lambda s: s["best_streak"] >= 7,
    },
    {
        "id": "xp_100",
        "icon": "🏁",
        "label": "100 XP Milestone",
        "check": lambda s: s["total_points"] >= 100,
    },
    {
        "id": "first_gem",
        "icon": "🏁",
        "label": "First Gem Earned",
        # This is an XP milestone (any points at all), not a check against
        # the real gems currency - kept as-is since it predates the
        # coins/gems split and renaming the id would orphan existing
        # UserAchievement rows.
        "check": lambda s: s["total_points"] >= 1,
    },
]

# Small additive gems bonus granted the moment an achievement is newly
# unlocked, on top of whatever (if anything) it already grants. Today no
# achievement grants points itself - this is the only reward tied to
# unlocking one.
ACHIEVEMENT_GEM_REWARD = 1


class AchievementService:
    def __init__(self, session: Session):
        self.session = session

    def _gather_stats(self, user_name: str, user) -> Dict[str, Any]:
        levels_completed = self.session.exec(
            select(func.count()).select_from(LevelProgress).where(
                LevelProgress.user_id == user.id,
                LevelProgress.status == "completed",
            )
        ).one()

        streak_info = StreakManager(self.session).get_user_streak(user.id)
        defeated_boss_ids = BossService(self.session).defeated_boss_ids(user_name)

        return {
            "total_points": user.total_points or 0,
            "best_streak": streak_info.get("best_streak", 0),
            "levels_completed": levels_completed,
            "defeated_boss_ids": defeated_boss_ids,
        }

    def list_for_user(self, user_name: str) -> List[dict]:
        """Returns every achievement's unlock state, persisting any
        newly-crossed threshold (with an unlock timestamp) the first time
        it's observed. Safe to call on every page load - already-unlocked
        achievements are never re-evaluated or re-timed."""
        manager = UserManager(self.session)
        user = manager.get_user(user_name)
        if not user:
            raise ValueError("User not found")

        unlocked_rows = self.session.exec(
            select(UserAchievement).where(UserAchievement.user_name == user_name)
        ).all()
        unlocked_map = {row.achievement_id: row.unlocked_at for row in unlocked_rows}

        stats = None
        newly_unlocked = False
        result = []
        for achievement in ACHIEVEMENTS:
            if achievement["id"] not in unlocked_map:
                if stats is None:
                    stats = self._gather_stats(user_name, user)
                if achievement["check"](stats):
                    record = UserAchievement(
                        user_name=user_name, achievement_id=achievement["id"]
                    )
                    self.session.add(record)
                    unlocked_map[achievement["id"]] = record.unlocked_at
                    newly_unlocked = True
                    user.gems = (user.gems or 0) + ACHIEVEMENT_GEM_REWARD
                    self.session.add(user)

            unlocked_at = unlocked_map.get(achievement["id"])
            result.append({
                "id": achievement["id"],
                "icon": achievement["icon"],
                "label": achievement["label"],
                "completed": unlocked_at is not None,
                "unlocked_at": unlocked_at.isoformat() if unlocked_at else None,
            })

        if newly_unlocked:
            self.session.commit()

        return result
