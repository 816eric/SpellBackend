from fastapi import APIRouter
from src.db_session import get_session
from src.models.word import SpellingWord
from src.services.word_manager import WordManager

router = APIRouter(prefix="/words", tags=["Words"])

@router.post("/")
def add_global_word(word: SpellingWord):
    with get_session() as session:
        manager = WordManager(session)
        return manager.add_word(word)

@router.post("/users/{name}/words/")
def add_user_word(name: str, word: SpellingWord):
    word.created_by = name
    word.is_personal = True
    with get_session() as session:
        manager = WordManager(session)
        return manager.add_word(word)

@router.get("/users/{name}/words/")
def get_words(name: str, tags: str = ""):
    tag_list = tags.split(",") if tags else []
    with get_session() as session:
        manager = WordManager(session)
        return manager.get_words_by_user_and_tags(name, tag_list)

@router.get("/users/{name}/tags/")
def get_tags(name: str):
    with get_session() as session:
        manager = WordManager(session)
        return manager.get_tags_by_user(name)