from fastapi import APIRouter
from src.db_session import get_session
from src.models.user import User
from src.services.user_manager import UserManager

router = APIRouter(prefix="/users", tags=["Users"])


# Create user (uses enhanced logic for default values)
@router.post("/")
def create_user(user: User):
    with get_session() as session:
        manager = UserManager(session)
        return manager.create_user(user)


# Get user profile (returns all profile fields)
@router.get("/{name}/profile")
def get_user_profile(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.get_user_profile(name)
from fastapi import Body
# Update user profile
@router.put("/{name}/profile")
def update_user_profile(name: str, profile: dict = Body(...)):
    profile.pop("name", None)  # Remove 'name' if present to avoid conflict
    with get_session() as session:
        manager = UserManager(session)
        return manager.update_user_profile(name, **profile)

@router.post("/{name}/login")
def log_login(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.log_login(name)