from sqlmodel import Session, select
from datetime import datetime
from src.models.minigame import MiniGame, UserMiniGameUnlock
from src.models.user import User
from src.models.reward import RewardHistory


class MiniGameManager:
    """Manages the game store catalog: unlocking and playing mini-games."""

    def __init__(self, session: Session):
        self.session = session

    def get_user_minigames(self, user_id: int) -> dict:
        """List all active mini-games with this user's unlock status."""
        games = self.session.exec(
            select(MiniGame).where(MiniGame.is_active == True)
        ).all()

        unlocked_query = select(UserMiniGameUnlock).where(
            UserMiniGameUnlock.user_id == user_id
        )
        unlocked_ids = {
            u.minigame_id for u in self.session.exec(unlocked_query).all()
        }

        user = self.session.get(User, user_id)

        return {
            "games": [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "icon": g.icon,
                    "gameType": g.game_type,
                    "nativeKey": g.native_key,
                    "unlockCost": g.unlock_cost,
                    "playCost": g.play_cost,
                    "unlocked": g.id in unlocked_ids or g.unlock_cost == 0,
                }
                for g in games
            ],
            "coins": user.total_points if user else 0,
        }

    def unlock_minigame(self, user_id: int, minigame_id: int) -> dict:
        """Spend points to permanently unlock a game."""
        user = self.session.get(User, user_id)
        game = self.session.get(MiniGame, minigame_id)

        if not user:
            return {"ok": False, "message": "User not found"}
        if not game or not game.is_active:
            return {"ok": False, "message": "Game not found"}

        already = self.session.exec(
            select(UserMiniGameUnlock).where(
                (UserMiniGameUnlock.user_id == user_id)
                & (UserMiniGameUnlock.minigame_id == minigame_id)
            )
        ).first()
        if already:
            return {"ok": False, "message": "Already unlocked"}

        if user.total_points < game.unlock_cost:
            return {"ok": False, "message": "Not enough coins"}

        user.total_points -= game.unlock_cost
        self.session.add(
            UserMiniGameUnlock(user_id=user_id, minigame_id=minigame_id)
        )
        self.session.add(RewardHistory(
            user_name=user.name,
            action="redeem",
            points=-game.unlock_cost,
            reason=f"unlock_game_{game.name}",
            timestamp=datetime.utcnow(),
        ))
        self.session.commit()

        return {
            "ok": True,
            "message": f"{game.name} unlocked!",
            "coins": user.total_points,
        }

    def play_minigame(self, user_id: int, minigame_id: int) -> dict:
        """Spend the per-play cost and hand back the game's embeddable URL."""
        user = self.session.get(User, user_id)
        game = self.session.get(MiniGame, minigame_id)

        if not user:
            return {"ok": False, "message": "User not found"}
        if not game or not game.is_active:
            return {"ok": False, "message": "Game not found"}

        unlocked = game.unlock_cost == 0 or self.session.exec(
            select(UserMiniGameUnlock).where(
                (UserMiniGameUnlock.user_id == user_id)
                & (UserMiniGameUnlock.minigame_id == minigame_id)
            )
        ).first()
        if not unlocked:
            return {"ok": False, "message": "Game not unlocked yet"}

        if user.total_points < game.play_cost:
            return {"ok": False, "message": "Not enough coins"}

        user.total_points -= game.play_cost
        if game.play_cost > 0:
            self.session.add(RewardHistory(
                user_name=user.name,
                action="redeem",
                points=-game.play_cost,
                reason=f"play_game_{game.name}",
                timestamp=datetime.utcnow(),
            ))
        self.session.commit()

        return {
            "ok": True,
            "gameType": game.game_type,
            "htmlUrl": game.html_url,
            "nativeKey": game.native_key,
            "coins": user.total_points,
        }
