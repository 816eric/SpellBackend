from fastapi import APIRouter, HTTPException, Depends, Header
from sqlmodel import select
from src.db_session import get_session
from src.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])

# Simple token-based admin protection (for example only)
def verify_admin_token(x_token: str = Header(...)):
    if x_token != "secret-admin-token":
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("/users")
def list_users(x_token: str = Depends(verify_admin_token)):
    with get_session() as session:
        users = session.exec(select(User)).all()
        return users

@router.delete("/users/{name}")
def delete_user(name: str, x_token: str = Depends(verify_admin_token)):
    with get_session() as session:
        user = session.get(User, name)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return {"message": f"User {name} deleted"}

@router.patch("/users/{name}/promote")
def promote_user_to_admin(name: str, x_token: str = Depends(verify_admin_token)):
    with get_session() as session:
        user = session.get(User, name)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_admin = True
        session.add(user)
        session.commit()
        return {"message": f"User {name} promoted to admin"}