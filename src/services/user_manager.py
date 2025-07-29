from sqlmodel import Session, select
from src.models.user import User
from src.models.history import LoginHistory
from datetime import datetime

class UserManager:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User):
        # Ensure all fields have default values if not provided
        user_data = user.dict()
        user_data.setdefault('age', None)
        user_data.setdefault('email', None)
        user_data.setdefault('phone', None)
        user_data.setdefault('school', None)
        user_data.setdefault('grade', None)
        user_data.setdefault('total_points', 0)
        new_user = User(**user_data)
        self.session.add(new_user)
        self.session.commit()
        return new_user
    def update_user_profile(self, name: str, **kwargs):
        """
        Update user profile fields. Only updates provided fields.
        """
        user = self.get_user(name)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.session.add(user)
        self.session.commit()
        return user

    def get_user_profile(self, name: str):
        """
        Return all profile fields for the user as a dict.
        """
        user = self.get_user(name)
        if not user:
            return None
        return user.dict()

    def get_user(self, name: str):
        return self.session.get(User, name)

    def log_login(self, name: str):
        login = LoginHistory(user_name=name, timestamp=datetime.now())
        self.session.add(login)
        self.session.commit()
        return login