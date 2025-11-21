from fastapi import APIRouter
from pydantic import BaseModel
from src.db_session import get_session
from src.models.word import SpellingWord
from sqlmodel import select
from src.models.user import User
from src.services.word_manager import WordManager
from src.services.tag_manager import TagManager

router = APIRouter(prefix="/words", tags=["Words"])

class BackCardUpdate(BaseModel):
    back_card: str

@router.post("/")
def add_global_word(word: SpellingWord):
    with get_session() as session:
        manager = WordManager(session)
        return manager.add_word(word, user_id=None)

@router.post("/users/{name}/words/")
def add_user_word(name: str, word: SpellingWord, tag: str = None):
    with get_session() as session:
        user = session.exec(select(User).where(User.name == name)).first()
        if not user:
            return {"error": "User not found"}
        word.created_by = user.id
        manager = WordManager(session)
        return manager.add_word(word, tag=tag, user_id=user.id)

@router.get("/users/{name}/words/")
def get_words(name: str, tags: str = ""):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    with get_session() as session:
        user = session.exec(select(User).where(User.name == name)).first()
        if not user:
            return []
        manager = WordManager(session)
        return manager.get_words_by_user_and_tags(user.id, tag_list)

@router.get("/users/{name}/tags/")
def get_tags(name: str):
    with get_session() as session:
        user = session.exec(select(User).where(User.name == name)).first()
        if not user:
            return []
        manager = WordManager(session)
        return manager.get_tags_by_user(user.id)

@router.put("/{word_id}/back-card")
def update_back_card(word_id: int, data: BackCardUpdate):
    """Update the back_card field for a word"""
    with get_session() as session:
        word = session.get(SpellingWord, word_id)
        if not word:
            return {"error": "Word not found"}
        word.back_card = data.back_card
        session.add(word)
        session.commit()
        session.refresh(word)
        return word

@router.get("/{word_id}/back-card")
def get_back_card(word_id: int):
    """Get the back_card for a specific word"""
    with get_session() as session:
        word = session.get(SpellingWord, word_id)
        if not word:
            return {"error": "Word not found"}
        return {"back_card": word.back_card}
    

## This endpoint is now redundant; use get_words with tags param instead