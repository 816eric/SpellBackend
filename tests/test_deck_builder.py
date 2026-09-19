from datetime import timedelta
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.services.deck_builder import DeckBuilder
from src.services.lesson_manager import LessonManager
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
    for i in range(12):
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

    # 12 words -> two balanced checkpoints of 6; checkpoint 1 is the second.
    assert sorted(c["word_id"] for c in cards) == sorted(ids[6:12])


def test_out_of_range_checkpoint_clamps_to_the_last_valid_chunk(session: Session):
    """A stale/malformed checkpoint index (e.g. requesting checkpoint 5 on a
    lesson that only has 2) should clamp to the nearest valid checkpoint,
    not silently fall back to the entire unscoped lesson."""
    user = User(name="TESTUSER", grade="P3")
    session.add(user)
    session.commit()
    session.refresh(user)

    tag = Tag(tag="TEST::P3::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    ids = []
    for i in range(12):
        w = SpellingWord(text=f"word{i}", language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        ids.append(w.id)
    session.commit()

    builder = DeckBuilder(session)
    cards, _ = builder.build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::EN::Week1", checkpoint=99
    )

    # 12 words -> two checkpoints of 6 (index 0, 1). checkpoint=99 clamps to
    # the last valid chunk (index 1), not the full 12-word pool.
    assert sorted(c["word_id"] for c in cards) == sorted(ids[6:12])


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


def test_lesson_manager_checkpoint_index_agrees_with_deck_builder_scoping(session: Session):
    """The checkpoint_index /lessons reports as "current" must be a valid
    input to /deck?checkpoint=, returning exactly that chunk's words - if
    LessonManager's and DeckBuilder's independent word-ordering/grouping
    queries ever drift apart, this is what would catch it."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    # 18 words -> checkpoints of 5,5,4,4. First 5 (checkpoint 0) fully
    # mastered -> checkpoint_index should be 1 (the second chunk).
    tag = Tag(tag="T::P1::EN::Week1", created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    word_ids = []
    for i in range(18):
        w = SpellingWord(text=f"word{i}", language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        word_ids.append(w.id)
    session.commit()

    for wid in word_ids[:5]:
        session.add(ReviewState(user_name="TESTUSER", word_id=wid, repetitions=5))
    session.commit()

    lesson_manager = LessonManager(session)
    lessons = lesson_manager.list_lessons_for_user(user, "EN")
    assert lessons[0]["checkpoint_index"] == 1

    deck_builder = DeckBuilder(session)
    cards, _ = deck_builder.build_daily_deck(
        "TESTUSER", limit=10, tag="T::P1::EN::Week1",
        checkpoint=lessons[0]["checkpoint_index"],
    )

    # checkpoint 1 (0-indexed) is the second chunk of 5 -> words 6-10 (the
    # 6th through 10th words created, 0-indexed word_ids[5:10]). The mastered
    # words from checkpoint 0 may ride along as flagged spaced-review extras.
    own = [c["word_id"] for c in cards if not c["state"].get("review")]
    assert sorted(own) == sorted(word_ids[5:10])


def _make_words(session, tag_str, n, prefix="w"):
    tag = Tag(tag=tag_str, created_by="admin")
    session.add(tag)
    session.commit()
    session.refresh(tag)
    ids = []
    for i in range(n):
        w = SpellingWord(text=f"{prefix}{i}", language="english")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        ids.append(w.id)
    session.commit()
    return ids


def test_checkpoint_deck_mixes_in_due_words_from_the_lessons_other_checkpoints(session: Session):
    session.add(User(name="TESTUSER", grade="P3"))
    session.commit()
    ids = _make_words(session, "TEST::P3::EN::Week1", 10)
    today = Scheduler.today_sg()
    # Checkpoint 0 words were studied and are due again; one is not due yet.
    for wid in ids[:4]:
        session.add(ReviewState(user_name="TESTUSER", word_id=wid, repetitions=1, due_date=today))
    session.add(ReviewState(
        user_name="TESTUSER", word_id=ids[4], repetitions=1,
        due_date=today + timedelta(days=3),
    ))
    session.commit()

    cards, _ = DeckBuilder(session).build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::EN::Week1", checkpoint=1
    )

    own = [c["word_id"] for c in cards if not c["state"].get("review")]
    extra = [c["word_id"] for c in cards if c["state"].get("review")]
    assert sorted(own) == sorted(ids[5:10])
    assert len(extra) == 3  # ceil(5 / 2)
    assert set(extra) <= set(ids[:4])  # due ones only, never the not-yet-due word


def test_checkpoint_deck_adds_one_due_word_from_an_earlier_lesson(session: Session):
    session.add(User(name="TESTUSER", grade="P3"))
    session.commit()
    old_ids = _make_words(session, "TEST::P3::EN::Week1", 5, prefix="old")
    new_ids = _make_words(session, "TEST::P3::EN::Week2", 5, prefix="new")
    today = Scheduler.today_sg()
    session.add(ReviewState(user_name="TESTUSER", word_id=old_ids[0], repetitions=2, due_date=today))
    session.commit()

    cards, _ = DeckBuilder(session).build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::EN::Week2", checkpoint=0
    )

    assert [c["word_id"] for c in cards if c["state"].get("review")] == [old_ids[0]]
    assert sorted(c["word_id"] for c in cards if not c["state"].get("review")) == sorted(new_ids)


def test_review_extras_never_cross_languages(session: Session):
    """A due English word from an earlier lesson must not turn up in a
    Chinese lesson's session (or the reverse)."""
    session.add(User(name="TESTUSER", grade="P3"))
    session.commit()
    en_ids = _make_words(session, "TEST::P3::EN::Week1", 3, prefix="eng")

    cn_tag = Tag(tag="TEST::P3::CN::第一课", created_by="admin")
    session.add(cn_tag)
    session.commit()
    session.refresh(cn_tag)
    cn_ids = []
    for ch in "你好我他她":
        w = SpellingWord(text=ch, language="chinese")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=cn_tag.id))
        cn_ids.append(w.id)
    session.commit()

    today = Scheduler.today_sg()
    for wid in en_ids:
        session.add(ReviewState(user_name="TESTUSER", word_id=wid, repetitions=2, due_date=today))
    session.commit()

    cards, _ = DeckBuilder(session).build_daily_deck(
        "TESTUSER", limit=10, tag="TEST::P3::CN::第一课", checkpoint=0
    )
    assert sorted(c["word_id"] for c in cards) == sorted(cn_ids)

    review_cards, _ = DeckBuilder(session).build_daily_deck(
        "TESTUSER", limit=15, tag="TEST::P3::CN::第一课", mode="review"
    )
    assert {c["word_id"] for c in review_cards} <= set(cn_ids)


def test_review_mode_covers_the_whole_lesson_weakest_first(session: Session):
    session.add(User(name="TESTUSER", grade="P3"))
    session.commit()
    ids = _make_words(session, "TEST::P3::EN::Week1", 8)
    today = Scheduler.today_sg()
    session.add(ReviewState(user_name="TESTUSER", word_id=ids[5], repetitions=1, due_date=today, fail_count=3))
    session.add(ReviewState(user_name="TESTUSER", word_id=ids[2], repetitions=4, due_date=today))
    session.commit()

    cards, _ = DeckBuilder(session).build_daily_deck(
        "TESTUSER", limit=5, tag="TEST::P3::EN::Week1", mode="review"
    )

    got = [c["word_id"] for c in cards]
    assert len(got) == 4  # limit 5 less 1 slot reserved for earlier lessons
    assert got[0] == ids[5]  # most-missed first
    assert ids[2] not in got  # well-known word is the last to be picked
