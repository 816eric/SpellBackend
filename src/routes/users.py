from fastapi import APIRouter, Body, Form, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.db_session import get_session
from src.models.user import User
from src.security import hash_password, is_hashed, issue_token, verify_password as check_password
from src.services.user_manager import UserManager

router = APIRouter(prefix="/users", tags=["Users"])


class SignupRequest(BaseModel):
    """Only profile fields are accepted at sign-up - never points/coins/etc."""
    name: str = Field(min_length=1, max_length=40)
    password: Optional[str] = Field(default="", max_length=128)
    age: Optional[int] = Field(default=None, ge=0, le=150)
    email: Optional[str] = Field(default="", max_length=254)
    phone: Optional[str] = Field(default="", max_length=32)
    school: Optional[str] = Field(default="", max_length=120)
    grade: Optional[str] = Field(default="", max_length=32)


# Create user (password optional). Returns a bearer token for the new account.
@router.post("/")
def create_user(body: SignupRequest):
    with get_session() as session:
        manager = UserManager(session)
        data = body.model_dump(exclude_unset=True)
        if data.get("age") is None:
            data.pop("age", None)
        data["password"] = hash_password(data.get("password") or "")
        user = manager.create_user(User(**data))
        out = user.model_dump(exclude={"password"})
        out["token"] = issue_token(user.id, user.name)
        return out


# Get user profile (returns all profile fields except the password)
@router.get("/{name}/profile")
def get_user_profile(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.get_user_profile(name)


# Update user profile (whitelisted fields only; password is re-hashed)
@router.put("/{name}/profile")
def update_user_profile(name: str, profile: dict = Body(...)):
    profile.pop("name", None)  # Remove 'name' if present to avoid conflict
    with get_session() as session:
        manager = UserManager(session)
        user = manager.update_user_profile(name, **profile)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user.model_dump(exclude={"password"})


@router.post("/{name}/login")
def log_login(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.log_login(name)


@router.post("/{name}/verify-password")
def verify_password(name: str, password: str = Form("", max_length=128)):
    """Login. Rate limited per IP+user by AuthMiddleware. On success returns
    a bearer token that every other endpoint requires."""
    with get_session() as session:
        manager = UserManager(session)
        user = manager.get_user(name)
        # Same response for unknown user and wrong password (no enumeration).
        if not user or not check_password(password, user.password):
            return {"verified": False}
        if user.password and not is_hashed(user.password):
            user.password = hash_password(user.password)  # upgrade legacy plaintext
            session.add(user)
            session.commit()
        return {"verified": True, "token": issue_token(user.id, user.name)}


@router.delete("/{name}")
def delete_user(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.delete_user(name)
