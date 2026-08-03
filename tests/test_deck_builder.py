from datetime import timedelta
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.services.deck_builder import DeckBuilder
from src.services.scheduler import Scheduler
from src.models.user import User
from src.models.word import SpellingWord
from src.models.tag import Tag
from src.models.link import UserTagsLink, WordTagLink
from src.models.review_state import ReviewState


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user_with_word(session: Session, quiz):
    user = User(name="TESTUSER", grade="P3")
    session.add(user)
    session.commit()
    session.refresh(user)

    tag = Tag(tag="TEST::P3::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    word = SpellingWord(text="apple", language="english", quiz=quiz)
    session.add(word)
    session.commit()
    session.refresh(word)

    session.add(UserTagsLink(user_id=user.id, tag_id=tag.id))
    session.add(WordTagLink(word_id=word.id, tag_id=tag.id))
    session.commit()
    return user, word


def test_build_daily_deck_includes_quiz_field(session: Session):
    quiz_json = '{"question":"What is an apple?","options":["A fruit","A car"],"correct":0}'
    _make_user_with_word(session, quiz_json)

    builder = DeckBuilder(session)
    cards, empty_reason = builder.build_daily_deck("TESTUSER", limit=10)

    assert empty_reason == ""
    assert len(cards) == 1
    assert cards[0]["quiz"] == quiz_json


def test_build_daily_deck_quiz_field_defaults_to_none(session: Session):
    _make_user_with_word(session, None)

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck("TESTUSER", limit=10)

    assert cards[0]["quiz"] is None


def test_tag_scoped_deck_includes_words_not_yet_due(session: Session):
    """A lesson-scoped request (tag given) should return the lesson's
    words even if SM-2 scheduled them for a future date - the user
    explicitly picked this lesson, so it shouldn't come back empty just
    because everything in it was reviewed correctly recently."""
    user, word = _make_user_with_word(session, None)
    today = Scheduler.today_sg()
    session.add(ReviewState(
        user_name=user.name,
        word_id=word.id,
        repetitions=2,
        interval_days=6,
        ease_factor=2.6,
        due_date=today + timedelta(days=6),
    ))
    session.commit()

    builder = DeckBuilder(session)
    cards, empty_reason = builder.build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::EN::Week1"
    )

    assert empty_reason == ""
    assert len(cards) == 1
    assert cards[0]["word_id"] == word.id


def test_untagged_daily_deck_excludes_words_not_yet_due(session: Session):
    """The generic no-tag daily deck (the actual 'what's due today across
    everything' queue) should keep excluding not-yet-due words - only
    lesson-scoped requests bypass the due-date gate."""
    user, word = _make_user_with_word(session, None)
    today = Scheduler.today_sg()
    session.add(ReviewState(
        user_name=user.name,
        word_id=word.id,
        repetitions=2,
        interval_days=6,
        ease_factor=2.6,
        due_date=today + timedelta(days=6),
    ))
    session.commit()

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck("TESTUSER", limit=10)

    assert cards == []


def test_words_by_tag_are_returned_in_ascending_id_order(session: Session):
    """Chunking into checkpoints depends on a stable word order; the
    underlying query previously had no ORDER BY, so this locks down
    ascending word_id as that stable order."""
    user = User(name="TESTUSER", grade="P3")
    session.add(user)
    session.commit()
    session.refresh(user)

    tag = Tag(tag="TEST::P3::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    ids = []
    for text in ["zebra", "apple", "mango"]:
        w = SpellingWord(text=text, language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        ids.append(w.id)
    session.commit()

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck("TESTUSER", limit=10, tag="TEST::P3::EN::Week1")

    assert [c["word_id"] for c in cards] == sorted(ids)


def test_checkpoint_param_scopes_deck_to_that_chunk_only(session: Session):
    user = User(name="TESTUSER", grade="P3")
    session.add(user)
    session.commit()
    session.refresh(user)

    tag = Tag(tag="TEST::P3::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    ids = []
    for i in range(7):
        w = SpellingWord(text=f"word{i}", language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        ids.append(w.id)
    session.commit()

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::EN::Week1", checkpoint=1
    )

    # Checkpoint 1 (0-indexed) is the second chunk of 5 words -> only the
    # 6th and 7th words (2 of them, since there are only 7 total).
    assert sorted(c["word_id"] for c in cards) == sorted(ids[5:7])


def test_deck_prioritizes_words_with_higher_fail_count(session: Session):
    """Within the same due-status tier, a word that's failed more should
    come back before one that's failed less, so it resurfaces sooner."""
    user = User(name="TESTUSER", grade="P3")
    session.add(user)
    session.commit()
    session.refresh(user)

    tag = Tag(tag="TEST::P3::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    today = Scheduler.today_sg()
    words = []
    for text in ["low_fail", "high_fail"]:
        w = SpellingWord(text=text, language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        words.append(w)
    session.commit()

    session.add(ReviewState(
        user_name="TESTUSER", word_id=words[0].id, repetitions=1,
        due_date=today, fail_count=1,
    ))
    session.add(ReviewState(
        user_name="TESTUSER", word_id=words[1].id, repetitions=1,
        due_date=today, fail_count=4,
    ))
    session.commit()

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck("TESTUSER", limit=10, tag="TEST::P3::EN::Week1")

    assert [c["text"] for c in cards] == ["high_fail", "low_fail"]
