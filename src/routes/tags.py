from fastapi import APIRouter
from src.services.tag_manager import TagManager

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("/")
def get_tags():
    return TagManager().get_predefined_tags()

@router.get("/users/{name}/tags/")
def get_user_tags(name: str):
    return TagManager().get_user_tags(name)