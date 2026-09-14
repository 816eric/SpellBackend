from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db_session import get_session_dep
from src.models.game import Challenge
from src.models.user import User
from datetime import datetime

router = APIRouter(prefix="/challenges", tags=["challenges"])

@router.post("/create")
def create_challenge(
    challenger_name: str,
    challengee_name: str,
    level_id: int,
    session: Session = Depends(get_session_dep)
):
    """Create a challenge between two users."""
    challenger = session.exec(select(User).where(User.name == challenger_name)).first()
    challengee = session.exec(select(User).where(User.name == challengee_name)).first()

    if not challenger or not challengee:
        raise HTTPException(status_code=404, detail="User not found")

    challenge = Challenge(
        challenger_id=challenger.id,
        challengee_id=challengee.id,
        level_id=level_id,
        status="pending"
    )
    session.add(challenge)
    session.commit()
    session.refresh(challenge)

    return {
        "challenge_id": challenge.id,
        "status": "pending",
        "message": f"Challenge sent to {challengee_name}!"
    }

@router.post("/{challenge_id}/accept")
def accept_challenge(challenge_id: int, session: Session = Depends(get_session_dep)):
    """Accept a challenge."""
    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    challenge.status = "accepted"
    session.add(challenge)
    session.commit()

    return {"challenge_id": challenge_id, "status": "accepted"}

@router.post("/{challenge_id}/complete")
def complete_challenge(
    challenge_id: int,
    winner_name: str,
    session: Session = Depends(get_session_dep)
):
    """Complete a challenge, determine winner."""
    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    winner = session.exec(select(User).where(User.name == winner_name)).first()
    if not winner:
        raise HTTPException(status_code=404, detail="Winner not found")

    challenge.status = "completed"
    challenge.completed_at = datetime.utcnow()
    challenge.winner_id = winner.id

    # Award points to winner
    winner.total_points += challenge.points_at_stake

    session.add_all([challenge, winner])
    session.commit()

    return {
        "challenge_id": challenge_id,
        "winner": winner_name,
        "points_awarded": challenge.points_at_stake
    }

@router.get("/user/{user_name}")
def get_user_challenges(user_name: str, session: Session = Depends(get_session_dep)):
    """Get user's challenges (pending and completed)."""
    user = session.exec(select(User).where(User.name == user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get challenges where user is challenger or challengee
    query = select(Challenge).where(
        (Challenge.challenger_id == user.id) | (Challenge.challengee_id == user.id)
    )
    challenges = session.exec(query).all()

    return {
        "user_name": user_name,
        "challenges": [
            {
                "id": c.id,
                "status": c.status,
                "level_id": c.level_id,
                "winner_id": c.winner_id
            }
            for c in challenges
        ]
    }
