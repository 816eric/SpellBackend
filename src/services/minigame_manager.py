from sqlmodel import Session, select
from datetime import datetime
from src.models.minigame import MiniGame, UserMiniGameUnlock
from src.models.user import User
from src.models.reward import RewardHistory

# Daily cap on combined minigame play time, across all games in the store.
DAILY_PLAYTIME_LIMIT_SECONDS = 15 * 60


class MiniGameManager:
    """Manages the game store catalog: unlocking and playing mini-games."""

    def __init__(self, session: Session):
        self.session = session

    def _playtime_status(self, user: User) -> dict:
        """Reset the counter if it's carried over from a previous day, then
        report where the user stands against the daily cap."""
        today = datetime.utcnow().date().isoformat()
        if user.playtime_date != today:
            user.playtime_date = today
            user.playtime_seconds_today = 0
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        used = user.playtime_seconds_today
        remaining = max(0, DAILY_PLAYTIME_LIMIT_SECONDS - used)
        return {
            "usedSeconds": used,
            "limitSeconds": DAILY_PLAYTIME_LIMIT_SECONDS,
            "remainingSeconds": remaining,
            "locked": remaining <= 0,
        }

    def get_playtime_status(self, user_id: int) -> dict:
        user = self.session.get(User, user_id)
        if not user:
            return {"ok": False, "message": "User not found"}
        status = self._playtime_status(user)
        return {"ok": True, **status}

    def add_playtime(self, user_id: int, seconds: int) -> dict:
        """Accumulate elapsed play seconds reported by the client (a
        heartbeat sent every few seconds while a game is open), and report
        back whether the daily cap has now been reached."""
        user = self.session.get(User, user_id)
        if not user:
            return {"ok": False, "message": "User not found"}

        status = self._playtime_status(user)
        if seconds > 0 and not status["locked"]:
            user.playtime_seconds_today += max(0, seconds)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            status = self._playtime_status(user)

        return {"ok": True, **status}

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
            "coins": user.coins if user else 0,
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

        if user.coins < game.unlock_cost:
            return {"ok": False, "message": "Not enough coins"}

        user.coins -= game.unlock_cost
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
            "coins": user.coins,
        }

    def play_minigame(self, user_id: int, minigame_id: int) -> dict:
        """Spend the per-play cost and hand back the game's embeddable URL."""
        user = self.session.get(User, user_id)
        game = self.session.get(MiniGame, minigame_id)

        if not user:
            return {"ok": False, "message": "User not found"}
        if not game or not game.is_active:
            return {"ok": False, "message": "Game not found"}

        if self._playtime_status(user)["locked"]:
            return {"ok": False, "message": "Daily play time limit reached"}

        unlocked = game.unlock_cost == 0 or self.session.exec(
            select(UserMiniGameUnlock).where(
                (UserMiniGameUnlock.user_id == user_id)
                & (UserMiniGameUnlock.minigame_id == minigame_id)
            )
        ).first()
        if not unlocked:
            return {"ok": False, "message": "Game not unlocked yet"}

        if user.coins < game.play_cost:
            return {"ok": False, "message": "Not enough coins"}

        user.coins -= game.play_cost
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
            "coins": user.coins,
        }
