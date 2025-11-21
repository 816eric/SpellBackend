from fastapi import APIRouter, Query
from src.db_session import get_session
from src.services.login_history import LoginHistoryService
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/login-history", tags=["LoginHistory"])

@router.post("/")
def add_login(user_name: str, tag: Optional[str] = None):
    with get_session() as session:
        service = LoginHistoryService(session)
        return service.add_login(user_name=user_name, timestamp=datetime.now(), tag=tag)

@router.get("/user/{user_name}")
def get_logins_for_user(user_name: str):
    with get_session() as session:
        service = LoginHistoryService(session)
        return service.get_logins_for_user(user_name)

@router.get("/")
def get_all_logins():
    with get_session() as session:
        service = LoginHistoryService(session)
        return service.get_all_logins()
