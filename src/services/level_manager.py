from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from src.models.game import Level, LevelProgress, LevelWord
from src.models.word import SpellingWord

class LevelManager:
    """Manages level CRUD and progression logic."""

    def __init__(self, session: Session):
        self.session = session

    def create_level(self, name: str, description: str, difficulty: int,
                     unlock_requirement: Optional[str] = None) -> Level:
        """Create a new level."""
        level = Level(
            name=name,
            description=description,
            difficulty=difficulty,
            unlock_requirement=unlock_requirement
        )
        self.session.add(level)
        self.session.commit()
        self.session.refresh(level)
        return level

    def add_words_to_level(self, level_id: int, word_ids: List[int]) -> None:
        """Add words to a level in order."""
        for position, word_id in enumerate(word_ids, 1):
            level_word = LevelWord(
                level_id=level_id,
                word_id=word_id,
                position=position
            )
            self.session.add(level_word)
        self.session.commit()

    def get_level_with_words(self, level_id: int) -> Optional[dict]:
        """Get level details including word list."""
        level = self.session.get(Level, level_id)
        if not level:
            return None

        # Get words in order
        words_query = select(SpellingWord).join(LevelWord).where(
            LevelWord.level_id == level_id
        ).order_by(LevelWord.position)
        words = self.session.exec(words_query).all()

        return {
            "id": level.id,
            "name": level.name,
            "description": level.description,
            "difficulty": level.difficulty,
            "words": [{"id": w.id, "text": w.text, "language": w.language} for w in words],
            "word_count": len(words)
        }

    def get_user_level_progress(self, user_id: int, level_id: int) -> Optional[LevelProgress]:
        """Get or create progress record for user-level pair."""
        query = select(LevelProgress).where(
            (LevelProgress.user_id == user_id) &
            (LevelProgress.level_id == level_id)
        )
        progress = self.session.exec(query).first()

        if not progress:
            # Create new progress record
            progress = LevelProgress(
                user_id=user_id,
                level_id=level_id,
                status="locked"
            )
            # Check if user should unlock (previous level complete or first level)
            if level_id == 1:
                progress.status = "in_progress"

            self.session.add(progress)
            self.session.commit()
            self.session.refresh(progress)

        return progress

    def check_level_unlock(self, user_id: int, level_id: int) -> bool:
        """Check if user can unlock this level."""
        level = self.session.get(Level, level_id)
        if not level or not level.unlock_requirement:
            return True  # No requirement, unlock automatically

        # Parse requirement: "complete_level_X" or "points_Y"
        if level.unlock_requirement.startswith("complete_level_"):
            required_level = int(level.unlock_requirement.split("_")[-1])
            query = select(LevelProgress).where(
                (LevelProgress.user_id == user_id) &
                (LevelProgress.level_id == required_level) &
                (LevelProgress.status == "completed")
            )
            return self.session.exec(query).first() is not None

        elif level.unlock_requirement.startswith("points_"):
            required_points = int(level.unlock_requirement.split("_")[-1])
            # Query User.total_points
            from src.models.user import User
            user = self.session.get(User, user_id)
            return user and user.total_points >= required_points

        return True

    def complete_level(self, user_id: int, level_id: int, accuracy: float) -> dict:
        """Mark level complete and award rewards."""
        progress = self.get_user_level_progress(user_id, level_id)

        # Award stars based on accuracy
        if accuracy >= 1.0:
            stars = 3
        elif accuracy >= 0.8:
            stars = 2
        else:
            stars = 1

        progress.status = "completed"
        progress.stars_earned = stars
        progress.points_earned = 10  # Level completion bonus
        progress.completed_at = datetime.utcnow()

        self.session.add(progress)
        self.session.commit()

        return {
            "level_id": level_id,
            "stars": stars,
            "points_bonus": 10,
            "message": f"Level complete! {stars} stars earned!"
        }

    def list_user_levels(self, user_id: int) -> List[dict]:
        """List all levels with user's progress."""
        levels = self.session.exec(select(Level).order_by(Level.id)).all()
        result = []

        for level in levels:
            progress = self.get_user_level_progress(user_id, level.id)
            can_unlock = self.check_level_unlock(user_id, level.id)

            if can_unlock and progress.status == "locked":
                progress.status = "in_progress"
                self.session.add(progress)
                self.session.commit()

            result.append({
                "id": level.id,
                "name": level.name,
                "difficulty": level.difficulty,
                "status": progress.status,
                "stars": progress.stars_earned,
                "study_count": progress.study_count
            })

        self.session.commit()
        return result
