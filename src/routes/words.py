import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db_session import get_session
from src.models.word import SpellingWord
from sqlmodel import select
from src.models.user import User
from src.services.word_manager import WordManager
from src.services.tag_manager import TagManager
from src.services.gemini_service import GeminiService

router = APIRouter(prefix="/words", tags=["Words"])
gemini = GeminiService(model="gemini-2.0-flash-exp")

class BackCardUpdate(BaseModel):
    back_card: str

class QuizUpdate(BaseModel):
    quiz: str

@router.post("/")
def add_global_word(word: SpellingWord):
    with get_session() as session:
        manager = WordManager(session)
        return manager.add_word(word, user_id=None)

@router.post("/users/{name}/words/")
def add_user_word(name: str, word: SpellingWord, tag: str = None, is_public: bool = False):
    with get_session() as session:
        name_upper = name.upper() if name else None
        user = session.exec(select(User).where(User.name == name_upper)).first()
        if not user:
            return {"error": "User not found"}
        word.created_by = user.id
        manager = WordManager(session)
        result = manager.add_word(word, tag=tag, user_id=user.id, is_public=is_public)
        return result

@router.get("/users/{name}/words/")
def get_words(name: str, tags: str = ""):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    with get_session() as session:
        name_upper = name.upper() if name else None
        user = session.exec(select(User).where(User.name == name_upper)).first()
        if not user:
            return []
        manager = WordManager(session)
        return manager.get_words_by_user_and_tags(user.id, tag_list)

@router.get("/users/{name}/tags/")
def get_tags(name: str):
    with get_session() as session:
        name_upper = name.upper() if name else None
        user = session.exec(select(User).where(User.name == name_upper)).first()
        if not user:
            return []
        manager = WordManager(session)
        return manager.get_tags_by_user(user.id)

@router.get("/quiz-pool")
def get_quiz_pool(limit: int = 100):
    """All words (any user, global) that have quiz data - the Word Snake
    game's Knowledge Stones fall back to this when a player's own deck
    doesn't happen to include any quiz-tagged words (most words in the
    database don't have quiz content yet, so most decks won't)."""
    with get_session() as session:
        words = session.exec(
            select(SpellingWord).where(SpellingWord.quiz.is_not(None)).limit(limit)
        ).all()
        return [
            {
                "word_id": w.id,
                "text": w.text,
                "language": w.language,
                "back_card": w.back_card,
                "quiz": w.quiz,
            }
            for w in words
        ]

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

@router.put("/{word_id}/quiz")
def update_quiz(word_id: int, data: QuizUpdate):
    """Update the quiz field for a word"""
    with get_session() as session:
        word = session.get(SpellingWord, word_id)
        if not word:
            return {"error": "Word not found"}
        word.quiz = data.quiz
        session.add(word)
        session.commit()
        session.refresh(word)
        return word

@router.get("/{word_id}/quiz")
def get_quiz(word_id: int):
    """Get the quiz for a specific word"""
    with get_session() as session:
        word = session.get(SpellingWord, word_id)
        if not word:
            return {"error": "Word not found"}
        return {"quiz": word.quiz}


@router.get("/{word_id}/quiz-explanation")
def get_quiz_explanation(word_id: int):
    """Why the quiz's correct answer is right, as one kid-friendly sentence
    (Word Snake's Knowledge Stone quiz shows this after the player answers).
    Generated once via Gemini and cached back onto the word's `quiz` JSON
    under an `explanation` key, so repeat plays of the same stone are
    instant and don't re-hit the LLM."""
    with get_session() as session:
        word = session.get(SpellingWord, word_id)
        if not word or not word.quiz:
            raise HTTPException(status_code=404, detail="Word or quiz not found")
        try:
            quiz_data = json.loads(word.quiz)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Malformed quiz data")

        cached = quiz_data.get("explanation")
        if cached:
            return {"explanation": cached}

        options = quiz_data.get("options") or []
        correct_idx = quiz_data.get("correct")
        if not isinstance(correct_idx, int) or not (0 <= correct_idx < len(options)):
            raise HTTPException(status_code=400, detail="Malformed quiz data")

        try:
            explanation = gemini.explain_quiz_answer(
                word=word.text,
                question=quiz_data.get("question", ""),
                options=options,
                correct_option=options[correct_idx],
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail="Explanation generation failed")

        quiz_data["explanation"] = explanation
        word.quiz = json.dumps(quiz_data)
        session.add(word)
        session.commit()
        return {"explanation": explanation}


## This endpoint is now redundant; use get_words with tags param instead