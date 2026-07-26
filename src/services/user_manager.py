from sqlmodel import Session, select
from src.models.user import User
from src.models.history import LoginHistory
from src.models.link import UserTagsLink
from src.models.word import SpellingWord
from src.models.tag import Tag
from fastapi import HTTPException
from datetime import datetime

class UserManager:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User):
        # Check if user already exists (case-insensitive)
        if not user.name:
            raise HTTPException(status_code=400, detail="User name is required")

        # Check for existing user with case-insensitive search
        from sqlalchemy import func
        existing_user = self.session.exec(
            select(User).where(func.upper(User.name) == user.name.upper())
        ).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="User already exists")

        # Ensure all fields have default values if not provided
        user_data = user.model_dump(exclude_unset=True)
        user_data.setdefault('age', "")
        user_data.setdefault('email', "")
        user_data.setdefault('phone', "")
        user_data.setdefault('school', "")
        user_data.setdefault('grade', "")
        user_data.setdefault('total_points', 0)
        # Keep name as provided (lowercase or as given), don't convert to uppercase
        # password is optional, do not enforce
        new_user = User(**user_data)
        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
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
            raise HTTPException(status_code=404, detail="User not found")
        return user.model_dump()

    def get_user(self, name: str):
        # Case-insensitive search for user
        if not name:
            return None
        from sqlalchemy import func
        return self.session.exec(select(User).where(func.upper(User.name) == name.upper())).first()

    def log_login(self, name: str):
        login = LoginHistory(user_name=name, timestamp=datetime.now())
        self.session.add(login)
        self.session.commit()
        return login

    def delete_user(self, name: str):
        """Delete a user and all their associated data."""
        user = self.get_user(name)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete all UserTagsLink entries for this user
        user_tag_links = self.session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user.id)).all()
        for link in user_tag_links:
            self.session.delete(link)
        
        # Delete/update tags created by this user
        tags_created_by_user = self.session.exec(select(Tag).where(Tag.created_by == user.id)).all()
        for tag in tags_created_by_user:
            # Check if other users still use this tag
            other_links = self.session.exec(select(UserTagsLink).where(UserTagsLink.tag_id == tag.id)).all()
            if other_links:
                # Transfer ownership to admin
                tag.created_by = "ADMIN"
                self.session.add(tag)
            else:
                # Delete the tag if no one uses it
                self.session.delete(tag)
        
        # Delete words created by this user
        words_created_by_user = self.session.exec(select(SpellingWord).where(SpellingWord.created_by == user.id)).all()
        for word in words_created_by_user:
            self.session.delete(word)
        
        # Delete login history for this user
        login_history = self.session.exec(select(LoginHistory).where(LoginHistory.user_name == user.name)).all()
        for log in login_history:
            self.session.delete(log)
        
        # Delete the user
        self.session.delete(user)
        self.session.commit()
        
        return {"success": True, "message": f"User {name} and all associated data deleted"}