from datetime import date, datetime, timedelta
from typing import Literal
from src.models.review_state import ReviewState

Quality = Literal[0,1,2,3,4,5]  # we'll use 0,1,3,5

class Scheduler:
    MIN_EASE = 1.3

    @staticmethod
    def today_sg() -> date:
        # For simplicity, use system date. Swap with timezone-aware if needed.
        return date.today()

    @classmethod
    def update_sm2(cls, state: ReviewState, quality: Quality) -> ReviewState:
        today = cls.today_sg()

        # clamp
        quality = 0 if quality < 0 else 5 if quality > 5 else quality

        if (
            quality >= 3
            and state.repetitions > 0
            and state.due_date is not None
            and state.due_date > today
        ):
            # Answered again before it was due (typically repeated within
            # the same study session). That's practice, not a spaced
            # recall, so it must not advance repetitions/interval - else a
            # word could reach "mastered" in one sitting.
            state.last_reviewed_at = datetime.now()
            return state

        if quality < 3:
            state.repetitions = 0
            state.interval_days = 1
            state.fail_count += 1
        else:
            if state.repetitions == 0:
                state.interval_days = 1
            elif state.repetitions == 1:
                state.interval_days = 6
            else:
                state.interval_days = int(round(state.interval_days * state.ease_factor))
            state.repetitions += 1

        # EF update (SM-2)
        ef = state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        state.ease_factor = max(cls.MIN_EASE, ef)

        state.due_date = today + timedelta(days=state.interval_days)
        state.last_reviewed_at = datetime.now()
        state.status = "review"
        return state
