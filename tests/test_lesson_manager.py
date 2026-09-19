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


def _make_sgp_lesson(session, tag_str, grade, subject, word_texts, reps_by_word):
    """Like `_make_lesson`, but under the SGP scope (no `user` needed since
    these fixtures aren't linked to any ReviewState)."""
    tag = Tag(tag=f"SGP::P{grade}::{subject}::{tag_str}", created_by="1")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    for i, text in enumerate(word_texts):
        w = SpellingWord(text=text, language="chinese", created_by="1")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
    session.commit()


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


def test_checkpoint_fields_for_a_partially_mastered_lesson(session: Session):
    """18 words -> 4 checkpoints (5,5,5,3). First 5 words fully mastered,
    the 6th (first word of checkpoint 2) is not -> checkpoint_index == 1."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    word_texts = [f"word{i}" for i in range(18)]
    reps = [5, 5, 5, 5, 5, 2] + [0] * 12
    _make_lesson(session, user, "Week1", 1, "EN", word_texts, reps)

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "EN")

    assert lessons[0]["checkpoint_count"] == 4
    assert lessons[0]["checkpoint_index"] == 1


def test_checkpoint_index_stays_on_last_chunk_when_lesson_fully_mastered(session: Session):
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    _make_lesson(session, user, "Week1", 1, "EN",
                 ["a", "b", "c", "d", "e"], [5, 5, 5, 5, 5])

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "EN")

    assert lessons[0]["checkpoint_count"] == 1
    assert lessons[0]["checkpoint_index"] == 0


def test_guest_is_pinned_to_sgp_p4_for_chinese_ignoring_own_grade(session: Session):
    """GUEST's own `grade` column (P1) is overridden for CN: it should only
    ever see SGP::P4 Chinese lessons, and never a same-grade lesson tagged
    under a different scope."""
    guest = User(name="GUEST", grade="P1")
    session.add(guest)
    session.commit()
    session.refresh(guest)

    _make_sgp_lesson(session, "第一课", 4, "CN", ["你", "好"], [0, 0])
    _make_sgp_lesson(session, "第二课", 1, "CN", ["我"], [0])  # wrong grade, wrong scope
    _make_lesson(session, guest, "Week1", 4, "CN", ["他"], [0])  # right grade, wrong scope

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(guest, "CN")

    assert [l["lesson_key"] for l in lessons] == ["第一课"]


def test_guest_gets_p1_english_from_any_scope(session: Session):
    """Unlike CN, GUEST's EN override only pins the grade (P1), not the
    scope, since P1 English isn't tagged under SGP at all."""
    guest = User(name="GUEST", grade="P1")
    session.add(guest)
    session.commit()
    session.refresh(guest)

    _make_lesson(session, guest, "Spelling 9", 1, "EN", ["cat"], [0])

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(guest, "EN")

    assert [l["lesson_key"] for l in lessons] == ["Spelling 9"]


def test_non_guest_user_is_not_scope_restricted(session: Session):
    """The SGP/scope pinning is GUEST-only - a real student with grade P4
    must still see their own (non-SGP) P4 Chinese lesson."""
    user = User(name="TESTUSER", grade="P4")
    session.add(user)
    session.commit()
    session.refresh(user)

    _make_lesson(session, user, "Week1", 4, "CN", ["他"], [0])

    manager = LessonManager(session)
    lessons = manager.list_lessons_for_user(user, "CN")

    assert [l["lesson_key"] for l in lessons] == ["Week1"]


def _record_pass(session, user, subject, lesson_key, index):
    from src.models.checkpoint_progress import CheckpointProgress
    session.add(CheckpointProgress(
        user_name=user.name, subject=subject, lesson_key=lesson_key, checkpoint_index=index,
    ))
    session.commit()


def test_lessons_report_each_checkpoints_words_and_passed_flag(session: Session):
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    ids = _make_lesson(session, user, "Week1", 1, "EN", [f"w{i}" for i in range(10)], [])
    _record_pass(session, user, "EN", "Week1", 0)

    lesson = LessonManager(session).list_lessons_for_user(user, "EN")[0]

    assert [c["word_ids"] for c in lesson["checkpoints"]] == [ids[:5], ids[5:]]
    assert [c["passed"] for c in lesson["checkpoints"]] == [True, False]
    assert lesson["checkpoint_index"] == 1
    assert lesson["status"] == "current"


def test_passing_a_checkpoint_does_not_need_word_mastery(session: Session):
    """Progress along the path is decoupled from spaced-repetition mastery."""
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    _make_lesson(session, user, "Week1", 1, "EN", list("abcde"), [1, 1, 1, 1, 1])
    _record_pass(session, user, "EN", "Week1", 0)

    lesson = LessonManager(session).list_lessons_for_user(user, "EN")[0]

    assert lesson["checkpoints"][0]["passed"] is True
    assert lesson["stars"] == 1  # mastery (stars) is still low
    assert lesson["status"] == "current"  # the review node is still ahead


def test_lesson_completes_when_points_and_review_are_passed(session: Session):
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    _make_lesson(session, user, "Week1", 1, "EN", list("abcde"), [])
    _make_lesson(session, user, "Week2", 1, "EN", ["f", "g"], [])
    manager = LessonManager(session)

    _record_pass(session, user, "EN", "Week1", 0)
    by_key = {l["lesson_key"]: l for l in manager.list_lessons_for_user(user, "EN")}
    assert by_key["Week1"]["review_passed"] is False
    assert by_key["Week2"]["status"] == "locked"

    _record_pass(session, user, "EN", "Week1", -1)
    by_key = {l["lesson_key"]: l for l in manager.list_lessons_for_user(user, "EN")}
    assert by_key["Week1"]["status"] == "completed"
    assert by_key["Week2"]["status"] == "current"


def test_review_cannot_be_passed_before_all_checkpoints(session: Session):
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    _make_lesson(session, user, "Week1", 1, "EN", [f"w{i}" for i in range(10)], [])
    _record_pass(session, user, "EN", "Week1", 0)
    _record_pass(session, user, "EN", "Week1", -1)

    lesson = LessonManager(session).list_lessons_for_user(user, "EN")[0]

    assert lesson["review_passed"] is False
    assert lesson["status"] == "current"


def test_review_due_count_counts_studied_words_due_today(session: Session):
    from datetime import date, timedelta
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    ids = _make_lesson(session, user, "Week1", 1, "EN", list("abcde"), [])
    today = date.today()
    session.add(ReviewState(user_name="TESTUSER", word_id=ids[0], repetitions=1, due_date=today))
    session.add(ReviewState(user_name="TESTUSER", word_id=ids[1], repetitions=1, due_date=today + timedelta(days=2)))
    session.commit()

    lesson = LessonManager(session).list_lessons_for_user(user, "EN")[0]

    assert lesson["review_due_count"] == 1


def test_label_type_filter_makes_each_type_its_own_track(session: Session):
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)
    _make_lesson(session, user, "Week1", 1, "EN", list("abcde"), [])
    _make_lesson(session, user, "Week2", 1, "EN", list("fghij"), [])
    moe = session.exec(__import__("sqlmodel").select(Tag).where(Tag.tag == "T::P1::EN::Week2")).one()
    moe.label_type = "MOE"
    session.add(moe)
    session.commit()
    manager = LessonManager(session)

    combined = {l["lesson_key"]: l["status"] for l in manager.list_lessons_for_user(user, "EN")}
    assert combined == {"Week1": "current", "Week2": "locked"}

    moe_only = manager.list_lessons_for_user(user, "EN", label_type="moe")
    assert [(l["lesson_key"], l["status"]) for l in moe_only] == [("Week2", "current")]
    teacher_only = manager.list_lessons_for_user(user, "EN", label_type="TEACHER")
    assert [(l["lesson_key"], l["status"]) for l in teacher_only] == [("Week1", "current")]


def test_lesson_with_a_spell_date_lists_without_error_and_flags_the_soonest_upcoming(session: Session):
    """Lessons carrying a parseable spell_date go through the upcoming-lesson
    lookup, which needs today's date - a regression test for it being used
    before assignment (which only shows up for dated lessons)."""
    from datetime import date, timedelta
    user = User(name="TESTUSER", grade="P1")
    session.add(user)
    session.commit()
    session.refresh(user)

    def dated(key, d):
        tag = Tag(
            tag=f"T::P1::EN::{key}", created_by="1",
            spell_date=f"{d.day} {d.strftime('%b').upper()} {d.year}",
        )
        session.add(tag)
        session.commit()
        session.refresh(tag)
        w = SpellingWord(text=f"w{key}", language="english", created_by="1")
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(WordTagLink(word_id=w.id, tag_id=tag.id))
        session.commit()

    today = date.today()
    dated("Week1", today - timedelta(days=30))  # already past
    dated("Week2", today + timedelta(days=20))
    dated("Week3", today + timedelta(days=5))   # soonest upcoming

    lessons = LessonManager(session).list_lessons_for_user(user, "EN")

    upcoming = [l["lesson_key"] for l in lessons if l["is_upcoming"]]
    assert upcoming == ["Week3"]
