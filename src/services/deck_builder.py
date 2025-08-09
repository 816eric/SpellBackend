from typing import List, Tuple, Dict
from sqlmodel import select, Session
from src.models.word import SpellingWord
from src.models.link import WordTagLink
from src.services.word_manager import WordManager
from src.services.user_manager import UserManager
from src.models.review_state import ReviewState
from src.services.scheduler import Scheduler

class DeckBuilder:
    def __init__(self, session: Session):
        self.session = session



    def build_daily_deck(self, user_name: str, limit: int = 10) -> Tuple[List[Dict], str]:
        """
        Returns (cards, empty_reason) where empty_reason in {'', 'no_tags', 'no_words'}
        """
        today = Scheduler.today_sg()

        user_manager = UserManager(self.session)
        user = user_manager.get_user(user_name)
        if not user:
            return ([], "no_tags")
        word_manager = WordManager(self.session)
        words = word_manager.get_all_words_for_user(user.id)
        print(f"Found {len(words)} words for user {user_name}")
        if not words:
            return ([], "no_words")

        pool_word_ids = [w.id for w in words]
        states = self.session.exec(
            select(ReviewState).where(
                (ReviewState.user_name == user_name) & (ReviewState.word_id.in_(pool_word_ids))
            )
        ).all()
        print(f"Found {len(states)} review states for user {user_name}")
        state_by_word = {s.word_id: s for s in states}

        overdue = []
        new_words = []
        for w in words:
            st = state_by_word.get(w.id)
            if st:
                due = st.due_date or today
                if due <= today:
                    overdue.append((w, st))
            else:
                new_words.append((w, None))

        overdue.sort(key=lambda item: ((item[1].due_date or today), item[1].ease_factor, item[0].id))

        cards: List[Dict] = []

        for w, st in overdue:
            if len(cards) >= limit:
                break
            cards.append({
                "word_id": w.id,
                "text": w.text,
                "language": w.language,
                "state": {
                    "repetitions": st.repetitions,
                    "interval_days": st.interval_days,
                    "ease_factor": st.ease_factor,
                    "due_date": (st.due_date or today).isoformat(),
                }
            })

        if len(cards) < limit:
            for w, _ in new_words:
                if len(cards) >= limit:
                    break
                cards.append({
                    "word_id": w.id,
                    "text": w.text,
                    "language": w.language,
                    "state": {
                        "repetitions": 0,
                        "interval_days": 0,
                        "ease_factor": 2.5,
                        "due_date": today.isoformat(),
                        "status": "new"
                    }
                })

        return (cards, "")
