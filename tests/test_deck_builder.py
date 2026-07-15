import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.services.deck_builder import DeckBuilder
from src.models.user import User
from src.models.word import SpellingWord
from src.models.tag import Tag
from src.models.link import UserTagsLink, WordTagLink


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
