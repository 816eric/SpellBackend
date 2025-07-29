from fastapi import APIRouter
from src.db_session import get_session
from src.models.user import User
from src.services.user_manager import UserManager

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/")
def create_user(user: User):
    with get_session() as session:
        manager = UserManager(session)
        return manager.create_user(user)

@router.get("/{name}")
def get_user(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.get_user(name)

@router.post("/{name}/login")
def log_login(name: str):
    with get_session() as session:
        manager = UserManager(session)
        return manager.log_login(name)