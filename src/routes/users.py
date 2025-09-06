from fastapi import HTTPException
from fastapi import APIRouter
from fastapi import Form
from src.db_session import get_session
from src.models.user import User
from src.services.user_manager import UserManager

router = APIRouter(prefix="/users", tags=["Users"])



# Create user (uses enhanced logic for default values, password optional)
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

# Update user profile (password can be updated if present)
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

@router.post("/{name}/verify-password")
def verify_password(name: str, password: str = Form(...)):
    with get_session() as session:
        manager = UserManager(session)
        user = manager.get_user(name)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_password = user.password if user.password is not None else ""
        print(f"Verifying password for user: {name}, provided: '{password}', stored: '{user_password}'")
        if user_password == password:
            return {"verified": True}
        else:
            return {"verified": False}