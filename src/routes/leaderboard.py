from typing import Optional
from typing import Optional
from fastapi import APIRouter, Depends, Header
from sqlmodel import Session
from ..db_session import get_session
from ..models.user import User
from ..services.leaderboard_s import LeaderboardService

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


# -------- OPTIONAL: current-user helper --------
# Swap this for your JWT dependency once auth is in place
def get_current_user_optional(
    session: Session = Depends(get_session),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name"),
) -> Optional[User]:
    """
    If you already have JWT auth:
      - Replace this with your `get_current_user()` dependency returning User.
    For now:
      - Read 'X-User-Name' header and load the user if exists.
    """
    if not x_user_name:
        return None
    return session.get(User, x_user_name)


@router.get("/top")
def leaderboard_top(
    limit: int = 20,
    school: Optional[str] = None,
    grade: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns top users by points (up to 20 by default).
    Auto-apply filters from current user if not provided and profile has values.
    """
    # Auto-apply school/grade from current user when missing
    effective_school = school if (school is not None and school != "") else (current_user.school if (current_user and current_user.school) else None)
    effective_grade = grade if (grade is not None and grade != "") else (current_user.grade if (current_user and current_user.grade) else None)

    svc = LeaderboardService(session)
    items, scope = svc.top(limit=limit, school=effective_school, grade=effective_grade)
    print(f"Returning top {items} users with scope: {scope}")
    return {
        "scope": scope,
        "count": len(items),
        "items": items,
    }


@router.get("/me")
def leaderboard_me(
    limit: int = 20,
    school: Optional[str] = None,
    grade: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Rank snapshot for the current user within the same filtered set.
    If no user header/JWT provided, returns anonymous.
    """
    if not current_user:
        return {"name": None, "rank": None, "total_points": None, "school": school, "grade": grade}

    effective_school = school if (school is not None and school != "") else (current_user.school if (current_user and current_user.school) else None)
    effective_grade = grade if (grade is not None and grade != "") else (current_user.grade if (current_user and current_user.grade) else None)

    svc = LeaderboardService(session)
    me = svc.rank_of_user(current_user.name, effective_school, effective_grade)
    if not me:
        # The user may be outside the filtered set or no longer exists in it
        return {
            "name": current_user.name,
            "rank": None,
            "total_points": current_user.total_points,
            "school": effective_school,
            "grade": effective_grade,
        }
    return me

# List all unique, non-empty, non-None school names
@router.get("/schools", response_model=list[str])
def list_schools(session: Session = Depends(get_session)):
    svc = LeaderboardService(session)
    return svc.list_schools()

# List all unique, non-empty, non-None grades, with optional school filter
@router.get("/grades", response_model=list[str])
def list_grades(school: Optional[str] = None, session: Session = Depends(get_session)):
    svc = LeaderboardService(session)
    return svc.list_grades(school)