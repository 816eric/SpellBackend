from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import select

from src.db_session import get_session
from src.models.user import User
from src.services.user_manager import UserManager
from src.models.word import SpellingWord
from src.models.history import StudyHistory
from src.models.reward import RewardHistory
from src.models.review_state import ReviewState
from src.services.scheduler import Scheduler
from src.services.deck_builder import DeckBuilder

router = APIRouter(prefix="/users", tags=["Study"])

class ReviewRequest(BaseModel):
    word_id: int
    quality: int  # 0,1,3,5

@router.get("/{name}/deck")
def get_daily_deck(name: str, limit: int = 10, tag: str = None):
    with get_session() as session:
        print(f"Fetching daily deck for user: {name} with limit: {limit} and tag: {tag}")
        manager = UserManager(session)
        user_profile = manager.get_user_profile(name)
        print(f"User found: {user_profile is not None}")
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found")
        builder = DeckBuilder(session)
        cards, empty_reason = builder.build_daily_deck(name, limit=limit, tag=tag)
        return {
            "date": Scheduler.today_sg().isoformat(),
            "cards": cards,
            "empty_reason": empty_reason or None
        }

@router.post("/{name}/review")
def submit_review(name: str, payload: ReviewRequest):
    now = datetime.now()
    with get_session() as session:
        manager = UserManager(session)
        user = manager.get_user(name)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        word = session.get(SpellingWord, payload.word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        state = session.get(ReviewState, (name, payload.word_id))
        if not state:
            state = ReviewState(
                user_name=name,
                word_id=payload.word_id,
                repetitions=0,
                interval_days=0,
                ease_factor=2.5
            )
            session.add(state)

        Scheduler.update_sm2(state, payload.quality)

        hist = session.get(StudyHistory, (name, payload.word_id))
        if hist:
            hist.count += 1
            hist.last_studied_at = now
        else:
            hist = StudyHistory(user_name=name, word_id=payload.word_id, count=1, last_studied_at=now)
            session.add(hist)

        user.total_points += 1
        session.add(RewardHistory(user_name=name, action="earn", points=1, reason="review", timestamp=now))

        session.commit()

        return {
            "updated_state": {
                "repetitions": state.repetitions,
                "interval_days": state.interval_days,
                "ease_factor": state.ease_factor,
                "due_date": state.due_date.isoformat() if state.due_date else None,
                "last_reviewed_at": state.last_reviewed_at.isoformat() if state.last_reviewed_at else None
            },
            "points_awarded": 1,
            "total_points": user.total_points
        }
