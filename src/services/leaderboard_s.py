from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select
from sqlalchemy import func
from datetime import datetime
from ..models.user import User  # expects fields: name, total_points, school?, grade?, last_point_earned_at?


class LeaderboardService:

    def list_grades(self, school: Optional[str] = None) -> List[str]:
        q = select(User.grade).distinct()
        if school:
            q = q.where(func.lower(User.school) == func.lower(school))
        results = self.session.exec(q).all()
        # Handle both tuple and ORM object results
        grades = []
        for row in results:
            if row is None:
                continue
            if isinstance(row, str):
                val = row.strip().upper()
            elif hasattr(row, "grade"):
                val = str(row.grade).strip().upper()
            elif isinstance(row, (tuple, list)):
                val = str(row[0]).strip().upper()
            else:
                continue
            if val and val.lower() != "none" and val not in grades:
                grades.append(val)
        print(f"Found {grades} unique grades")
        return sorted(grades)

    def list_schools(self) -> List[str]:
        q = select(User.school).distinct()
        results = self.session.exec(q).all()  
        print(f"result is {results}")      
        # Handle both tuple and ORM object results
        schools = []
        for row in results:
            if row is None:
                continue
            if isinstance(row, str):
                val = row.strip().upper()
            elif hasattr(row, "school"):
                val = str(row.school).strip().upper()
            elif isinstance(row, (tuple, list)):
                val = str(row[0]).strip().upper()
            else:
                continue
            if val and val.lower() != "none" and val not in schools:
                schools.append(val)
        print(f"Found {schools} unique schools")
        return sorted(schools)
    """
    Builds leaderboards with optional school/grade filters.
    Sorting:
      1) total_points DESC
      2) last_point_earned_at DESC (NULLs last)
      3) name ASC (case-insensitive)
    """

    def __init__(self, session: Session):
        self.session = session

    def _base_query(
        self,
        school: Optional[str],
        grade: Optional[str]
    ):
        q = select(User)
        if school:
            q = q.where(func.lower(User.school) == func.lower(school))
        if grade:
            q = q.where(func.lower(User.grade) == func.lower(grade))
        return q

    def _order(self, q):
        q = q.order_by(
            User.total_points.desc(),
            func.lower(User.name).asc(),
        )
        return q

    def top(
        self,
        limit: int = 20,
        school: Optional[str] = None,
        grade: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Optional[str]]]:
        limit = max(1, min(limit, 50))
        q = self._order(self._base_query(school, grade))
        users = [u for u in self.session.exec(q.limit(limit + 5)).all() if u.name.lower() != "admin"]

        items: List[Dict[str, Any]] = []
        for idx, u in enumerate(users[:limit], start=1):
            items.append({
                "rank": idx,
                "name": u.name,
                "total_points": u.total_points,
                "school": u.school,
                "grade": u.grade,
            })
        scope = {"school": school, "grade": grade}
        return items, scope

    def rank_of_user(
        self,
        user_name: str,
        school: Optional[str],
        grade: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Compute rank for a user within the same filtered set.
        Implementation: fetch up to a reasonable cap and enumerate.
        (Good enough for small/medium user bases; optimize later if needed.)
        """
        q = self._order(self._base_query(school, grade))
        # Cap to avoid huge memory; adjust if you expect many users
        users = [u for u in self.session.exec(q.limit(10000)).all() if u.name.lower() != "admin"]
        for idx, u in enumerate(users, start=1):
            if u.name == user_name:
                return {
                    "name": u.name,
                    "rank": idx,
                    "total_points": u.total_points,
                    "school": u.school,
                    "grade": u.grade,
                }
        return None
