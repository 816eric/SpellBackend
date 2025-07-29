from sqlmodel import Session, select
from src.models.history import LoginHistory
from typing import List, Optional

class LoginHistoryService:
    def __init__(self, session: Session):
        self.session = session

    def add_login(self, user_name: str, timestamp, tag: Optional[str] = None):
        login = LoginHistory(user_name=user_name, timestamp=timestamp, tag=tag)
        self.session.add(login)
        self.session.commit()
        return login

    def get_logins_for_user(self, user_name: str) -> List[LoginHistory]:
        statement = select(LoginHistory).where(LoginHistory.user_name == user_name)
        return self.session.exec(statement).all()

    def get_all_logins(self) -> List[LoginHistory]:
        statement = select(LoginHistory)
        return self.session.exec(statement).all()
