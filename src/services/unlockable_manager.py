from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from src.models.game import Unlockable, UserUnlockable
from src.models.user import User
from src.models.reward import RewardHistory

class UnlockableManager:
    """Manages cosmetics inventory and redemption."""

    def __init__(self, session: Session):
        self.session = session

    def create_unlockable(self, type: str, name: str, description: str,
                         points_cost: int, unlock_method: str,
                         rarity: str = "common") -> Unlockable:
        """Create a new cosmetic reward."""
        unlockable = Unlockable(
            type=type,
            name=name,
            description=description,
            points_cost=points_cost,
            unlock_method=unlock_method,
            rarity=rarity
        )
        self.session.add(unlockable)
        self.session.commit()
        self.session.refresh(unlockable)
        return unlockable

    def get_user_unlockables(self, user_id: int) -> dict:
        """Get all unlockables with ownership status."""
        unlockables = self.session.exec(select(Unlockable)).all()

        owned_query = select(UserUnlockable).where(
            UserUnlockable.user_id == user_id
        )
        owned = self.session.exec(owned_query).all()
        owned_ids = {u.unlockable_id for u in owned}

        return {
            "available": [
                {
                    "id": u.id,
                    "type": u.type,
                    "name": u.name,
                    "points_cost": u.points_cost,
                    "rarity": u.rarity,
                    "owned": u.id in owned_ids,
                    "equipped": any(uo.is_equipped for uo in owned if uo.unlockable_id == u.id)
                }
                for u in unlockables
            ],
            "owned_count": len(owned_ids)
        }

    def redeem_unlockable(self, user_id: int, unlockable_id: int) -> dict:
        """Redeem points for a cosmetic."""
        user = self.session.get(User, user_id)
        unlockable = self.session.get(Unlockable, unlockable_id)

        if not user:
            return {"ok": False, "message": "User not found"}
        if not unlockable:
            return {"ok": False, "message": "Unlockable not found"}

        # Check already owned
        query = select(UserUnlockable).where(
            (UserUnlockable.user_id == user_id) &
            (UserUnlockable.unlockable_id == unlockable_id)
        )
        if self.session.exec(query).first():
            return {"ok": False, "message": "Already owned"}

        # Check points
        if user.total_points < unlockable.points_cost:
            return {"ok": False, "message": "Insufficient points"}

        # Deduct points
        user.total_points -= unlockable.points_cost

        # Add to inventory
        user_unlockable = UserUnlockable(
            user_id=user_id,
            unlockable_id=unlockable_id,
            is_equipped=False
        )
        self.session.add(user_unlockable)

        # Log redemption
        history = RewardHistory(
            user_name=user.name,
            action="redeem",
            points=-unlockable.points_cost,
            reason=f"cosmetic_{unlockable.name}",
            timestamp=datetime.utcnow()
        )
        self.session.add(history)
        self.session.commit()

        return {
            "ok": True,
            "message": f"Unlocked {unlockable.name}!",
            "remaining_points": user.total_points,
            "unlockable": {
                "id": unlockable.id,
                "name": unlockable.name,
                "type": unlockable.type
            }
        }

    def equip_cosmetic(self, user_id: int, unlockable_id: int) -> dict:
        """Set a cosmetic as active (one per type)."""
        # Get the unlockable to know its type
        unlockable = self.session.get(Unlockable, unlockable_id)
        if not unlockable:
            return {"ok": False, "message": "Unlockable not found"}

        # Check user owns it
        query = select(UserUnlockable).where(
            (UserUnlockable.user_id == user_id) &
            (UserUnlockable.unlockable_id == unlockable_id)
        )
        user_unlockable = self.session.exec(query).first()
        if not user_unlockable:
            return {"ok": False, "message": "Not owned"}

        # Unequip others of same type
        unequip_query = select(UserUnlockable).join(Unlockable).where(
            (UserUnlockable.user_id == user_id) &
            (Unlockable.type == unlockable.type) &
            (UserUnlockable.is_equipped == True)
        )
        for uo in self.session.exec(unequip_query).all():
            uo.is_equipped = False

        # Equip this one
        user_unlockable.is_equipped = True
        self.session.add(user_unlockable)
        self.session.commit()

        return {
            "ok": True,
            "message": f"{unlockable.name} equipped!",
            "equipped": unlockable.name
        }

    def seed_default_unlockables(self) -> None:
        """Seed database with default cosmetics."""
        defaults = [
            ("avatar_skin", "Blue Cat", "A friendly blue cat", 0, "earn_level_1", "common"),
            ("avatar_skin", "Rainbow Theme", "Colorful rainbow", 50, "redeem_points", "rare"),
            ("effect", "Gold Star", "Sparkling gold effect", 100, "redeem_points", "epic"),
            ("theme", "Dark Mode", "Easy on the eyes", 30, "redeem_points", "common"),
        ]

        for type_, name, desc, cost, method, rarity in defaults:
            existing = self.session.exec(
                select(Unlockable).where(Unlockable.name == name)
            ).first()
            if not existing:
                self.create_unlockable(type_, name, desc, cost, method, rarity)
