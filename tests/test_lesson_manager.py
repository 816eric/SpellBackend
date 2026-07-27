import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.services.lesson_manager import LessonManager
from src.models.user import User
from src.models.tag import Tag
from src.models.word import SpellingWord
from src.models.link import WordTagLink
from src.models.review_state import ReviewState


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.models import user, tag, word, link, review_state  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_lesson(session, user, tag_str, grade, subject, word_texts, reps_by_word):
    """Creates a P{grade}::{subject}::{tag_str} tag with len(word_texts) words,
    each linked via WordTagLink, and a ReviewState for `user` giving each word
    `reps_by_word[i]` repetitions (0 if not listed). Returns the list of
    created word ids, in the same order as `word_texts`, so callers can
    target a specific word afterward without re-querying."""
    tag = Tag(tag=f"T::P{grade}::{subject}::{tag_str}", created_by="1")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    word_ids = []
    for i, text in enumerate(word_texts):
        w = SpellingWord(text=text, language="english", created_by="1")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        reps = reps_by_word[i] if i < len(reps_by_word) else 0
        if reps:
            session.add(ReviewState(user_name=user.name, word_id=w.id, repetitions=reps))
        word_ids.append(w.id)
    session.commit()
    return word_ids


def test_lesson_at_80_percent_is_not_completed(session: Session):
    """4 of 5 words fully mastered (reps=5), 1 word untouched (reps=0) ->
    mastery_pct == 0.8, which must NOT unlock the next lesson or award 3 stars
    under the new 100%-required rule."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    _make_lesson(session, user, "Week1", 1, "EN",
                 ["a", "b", "c", "d", "e"], [5, 5, 5, 5, 0])

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "EN")

    assert len(lessons) == 1
    assert lessons[0]["mastery_pct"] == 0.8
    assert lessons[0]["status"] == "current"
    assert lessons[0]["stars"] == 2


def test_lesson_at_100_percent_is_completed_with_3_stars(session: Session):
    """All words fully mastered -> mastery_pct == 1.0, status completed, 3 stars."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    _make_lesson(session, user, "Week1", 1, "EN",
                 ["a", "b", "c", "d", "e"], [5, 5, 5, 5, 5])

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "EN")

    assert lessons[0]["mastery_pct"] == 1.0
    assert lessons[0]["status"] == "completed"
    assert lessons[0]["stars"] == 3


def test_second_lesson_unlocks_only_once_first_hits_100_percent(session: Session):
    """With two lessons, the second must stay 'locked' while the first is at
    80% (previously enough to unlock it), and become 'current' once the first
    reaches 100%."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    week1_word_ids = _make_lesson(session, user, "Week1", 1, "EN",
                                   ["a", "b", "c", "d", "e"], [5, 5, 5, 5, 0])  # 80%
    _make_lesson(session, user, "Week2", 1, "EN",
                 ["f", "g"], [])  # untouched

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "EN")

    by_key = {l["lesson_key"]: l for l in lessons}
    assert by_key["Week1"]["status"] == "current"
    assert by_key["Week2"]["status"] == "locked"

    # Bump the 5th word ("e") in Week1 up to full mastery -> Week1 hits 100%.
    session.add(ReviewState(user_name=user.name, word_id=week1_word_ids[4], repetitions=5))
    session.commit()

    lessons2 = manager.list_lessons_for_user(user, "EN")
    by_key2 = {l["lesson_key"]: l for l in lessons2}
    assert by_key2["Week1"]["status"] == "completed"
    assert by_key2["Week2"]["status"] == "current"
