from sqlmodel import Session, select
from src.models.user import User
from src.models.history import LoginHistory
from datetime import datetime

class UserManager:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User):
        self.session.add(user)
        self.session.commit()
        return user

    def get_user(self, name: str):
        return self.session.get(User, name)

    def log_login(self, name: str):
        login = LoginHistory(user_name=name, timestamp=datetime.now())
        self.session.add(login)
        self.session.commit()
        return login