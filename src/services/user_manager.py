from sqlmodel import Session, select
from src.models.user import User
from src.models.history import LoginHistory
from fastapi import HTTPException
from datetime import datetime

class UserManager:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User):
        # Check if user already exists
        statement = select(User).where(User.name == user.name.upper() if user.name else None)
        existing_user = self.session.exec(statement).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="User already exists")
        
        # Ensure all fields have default values if not provided
        user_data = user.dict()
        user_data.setdefault('age', "")
        user_data.setdefault('email', "")
        user_data.setdefault('phone', "")
        user_data.setdefault('school', "")
        user_data.setdefault('grade', "")
        user_data.setdefault('total_points', 0)
        # Ensure name, school, and grade are uppercase if present
        if user_data['name']:
            user_data['name'] = str(user_data['name']).upper()
        if user_data['school']:
            user_data['school'] = str(user_data['school']).upper()
        if user_data['grade']:
            user_data['grade'] = str(user_data['grade']).upper()
        # password is optional, do not enforce
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
            if key in ("name", "school", "grade", "email") and value:
                value = str(value).upper()
            if key == "password":
                # allow password update if present
                setattr(user, key, value)
            elif hasattr(user, key):
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
        return self.session.exec(select(User).where(User.name == name)).first()

    def log_login(self, name: str):
        login = LoginHistory(user_name=name, timestamp=datetime.now())
        self.session.add(login)
        self.session.commit()
        return login