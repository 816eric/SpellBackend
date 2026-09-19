import re
from datetime import date
from typing import Optional, List, Dict, Tuple
from sqlmodel import Session, select
from src.models.tag import Tag
from src.models.link import WordTagLink
from src.models.review_state import ReviewState
from src.models.checkpoint_progress import CheckpointProgress
from src.services.checkpoints import (
    MASTERY_REPS,
    REVIEW_CHECKPOINT_INDEX,
    chunk_word_ids,
    current_checkpoint_index,
    is_word_mastered,
    passed_checkpoint_indices,
)
from src.models.user import User

# Chinese numerals used in lesson tags like "第一课" (Lesson 1).
CJK_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# Single-digit Chinese numerals, used to build up two-digit values (11-31)
# for parsing dates like "十一" (11) or "二十五" (25) - CJK_NUM_MAP alone
# only covers 1-10.
_CJK_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

_SKILL_KEYWORDS = {"read", "write", "listen", "speak"}

_DATE_RE = re.compile(r"([0-9一二三四五六七八九十]+)月([0-9一二三四五六七八九十]+)日")

# English-curriculum spell dates look like "16 JUL 2026" (day, 3-letter
# month abbreviation, year) - a different shape from the Chinese
# "<month>月<day>日" convention, and unlike it, they do carry a year.
_EN_DATE_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\b")
_MONTH_ABBR = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _cjk_numeral_to_int(s: str) -> Optional[int]:
    """Parses a 1-99 value written as digits or Chinese numerals
    ('十一' -> 11, '二十五' -> 25, '30' -> 30). Returns None for anything
    else (bigger numbers, mixed garbage, empty string)."""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if not all(ch in _CJK_DIGITS or ch == "十" for ch in s):
        return None
    if s == "十":
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CJK_DIGITS.get(left, 1) if left else 1
        ones = _CJK_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(s) == 1:
        return _CJK_DIGITS.get(s)
    return None


def parse_spell_date(date_str: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """Parses a lesson's free-text spell date into a (year, month, day)
    tuple for sorting. Supports two source formats:
    - Chinese: '<month>月<day>日' in digits or Chinese numerals (e.g.
      '七月十四日' or '7月14日') - no year, so year comes back as 0.
    - English: 'D MON YYYY' (e.g. '16 JUL 2026').
    A lesson's own tags never mix subjects, and list_lessons_for_user
    always sorts one subject at a time, so a Chinese lesson's yearless
    (0, month, day) tuples are never compared against an English lesson's
    dated ones - only within their own subject's lesson list, where every
    entry uses the same format consistently.
    Returns None for missing/unparseable/out-of-range dates - callers
    should treat those as "no date" rather than erroring."""
    if not date_str:
        return None
    m = _DATE_RE.search(date_str)
    if m:
        month = _cjk_numeral_to_int(m.group(1))
        day = _cjk_numeral_to_int(m.group(2))
        if month is not None and day is not None and 1 <= month <= 12 and 1 <= day <= 31:
            return (0, month, day)
    m2 = _EN_DATE_RE.search(date_str)
    if m2:
        day = int(m2.group(1))
        month = _MONTH_ABBR.get(m2.group(2).upper())
        year = int(m2.group(3))
        if month is not None and 1 <= day <= 31:
            return (year, month, day)
    return None


def resolve_spell_date(date_tuple: Tuple[int, int, int], today: date) -> Optional[date]:
    """Turns a `parse_spell_date()` tuple into a concrete calendar `date`
    relative to `today`. Chinese dates carry no year (year=0 in the tuple);
    those are assumed to fall in the current year, rolling over to next
    year if that date has already passed - since the Chinese curriculum's
    dates are recurring and always meant to refer to an upcoming lesson,
    not one from a year ago. Returns None for an invalid calendar date
    (e.g. day out of range for that month)."""
    year, month, day = date_tuple
    if year == 0:
        year = today.year
        try:
            resolved = date(year, month, day)
        except ValueError:
            return None
        if resolved < today:
            try:
                resolved = date(year + 1, month, day)
            except ValueError:
                return None
        return resolved
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_lesson_tag(tag_str: str) -> Optional[Dict]:
    """Parse a curriculum tag like 'SMSP::P3::EN::Week4' or
    'Eric::P3::CN::第一课::read' into structured fields.

    Expected convention: <scope>::<grade>::<subject>::<lesson...>[::<skill>],
    but the subject isn't always the 3rd segment - tags like
    'SMSP::P1::Term3::CN::听写(十一)' insert an extra classifier segment
    (e.g. a term marker) between grade and subject, so the subject token
    (EN/CN) is located by scanning rather than assumed to be at a fixed
    position.
    Returns None for tags that don't follow this convention (ad-hoc/test tags
    such as 'TEST::TAG' or 'ONBLY FOR BOBO' are intentionally excluded from
    lesson listings).
    """
    parts = [p.strip() for p in tag_str.split("::") if p.strip()]
    if len(parts) < 4:
        return None

    scope, grade = parts[0], parts[1]
    if not re.match(r"^P\d+$", grade, re.IGNORECASE):
        return None

    subject_idx = None
    for i in range(2, len(parts)):
        if parts[i].upper() in ("EN", "CN"):
            subject_idx = i
            break
    if subject_idx is None:
        return None
    subject = parts[subject_idx]

    prefix = parts[2:subject_idx]
    rest = parts[subject_idx + 1:]
    skill = None
    if rest and rest[-1].lower() in _SKILL_KEYWORDS:
        skill = rest[-1].lower()
        rest = rest[:-1]
    if not rest:
        return None

    lesson_key = " ".join(rest)

    term = 0
    week = None
    cjk_num = None
    for p in prefix + rest:
        m = re.match(r"Term(\d+)", p, re.IGNORECASE)
        if m:
            term = int(m.group(1))
        m2 = re.match(r"Week(\d+)", p, re.IGNORECASE)
        if m2:
            week = int(m2.group(1))
        m3 = re.match(r"第([一二三四五六七八九十]+)课", p)
        if m3 and m3.group(1) in CJK_NUM_MAP:
            cjk_num = CJK_NUM_MAP[m3.group(1)]

    order = week if week is not None else (cjk_num if cjk_num is not None else 999)

    return {
        "scope": scope,
        "grade": grade.upper(),
        "subject": subject.upper(),
        "lesson_key": lesson_key,
        "skill": skill,
        "sort_key": (term, order),
    }


def _prettify(lesson_key: str) -> str:
    """'Week4' -> 'Week 4', 'Term4 Week1(...)' -> 'Term 4 Week 1(...)'."""
    return re.sub(r"([A-Za-z])(\d)", r"\1 \2", lesson_key)


class LessonManager:
    """Builds a grade/subject-filtered, progress-aware lesson list from the
    Tag system, for the Duolingo-style journey path UI."""

    # Words with this many spaced-repetition reps count as "fully learned"
    # for mastery-percentage (stars) purposes.
    _MASTERY_REPS = MASTERY_REPS

    def __init__(self, session: Session):
        self.session = session

    # GUEST is a shared, unauthenticated identity (see FlutterSpell_Game's
    # GameProvider.loginAsGuest) - unlike a real student it has no teacher
    # assigning it a specific curriculum, so it's hard-pinned to one curated
    # lesson set per subject rather than seeing every scope/grade's content.
    # Chosen to match what's actually tagged: SGP only has Chinese content
    # at P4 (no P1 Chinese tag parses cleanly), while P1 English lives
    # untagged-by-scope-restriction (e.g. SMSP) since SGP has none.
    _GUEST_OVERRIDES = {
        "CN": {"grade": "P4", "scope": "SGP"},
        "EN": {"grade": "P1", "scope": None},
    }

    def list_lessons_for_user(
        self, user: User, subject: str, label_type: Optional[str] = None
    ) -> List[Dict]:
        """`label_type` (e.g. 'TEACHER', 'MOE') restricts the list to
        lessons of that type, and the completed/current/locked sequence is
        then computed within just those lessons - each type is its own
        track. None means every type in one combined sequence."""
        subject = subject.upper()
        label_type = label_type.upper() if label_type else None
        grade = (user.grade or "").upper()
        scope_filter = None
        if (user.name or "").upper() == "GUEST":
            override = self._GUEST_OVERRIDES.get(subject)
            if override:
                grade = override["grade"]
                scope_filter = override["scope"]

        all_tags = self.session.exec(select(Tag)).all()
        groups: Dict[str, Dict] = {}
        for tag in all_tags:
            parsed = parse_lesson_tag(tag.tag)
            if not parsed:
                continue
            if parsed["grade"] != grade or parsed["subject"] != subject:
                continue
            if scope_filter and parsed["scope"].upper() != scope_filter:
                continue
            if label_type and (tag.label_type or "TEACHER").upper() != label_type:
                continue
            key = parsed["lesson_key"]
            group = groups.setdefault(key, {
                "lesson_key": key,
                "display_name": _prettify(key),
                "label_type": tag.label_type or "TEACHER",
                "tags": [],
                "tag_ids": [],
                "skills": [],
                "sort_key": parsed["sort_key"],
                "spell_date": None,
            })
            group["tags"].append(tag.tag)
            group["tag_ids"].append(tag.id)
            if parsed["skill"] and parsed["skill"] not in group["skills"]:
                group["skills"].append(parsed["skill"])
            if not group["spell_date"] and tag.spell_date:
                group["spell_date"] = tag.spell_date

        # Lessons with a parseable spell date sort chronologically ahead of
        # everything else; lessons without one keep the existing
        # Week#/第几课-derived order (falling back to their natural,
        # roughly-import-ordered position when neither is present).
        def _sort_key(g):
            date_tuple = parse_spell_date(g["spell_date"])
            return (0, date_tuple) if date_tuple else (1, g["sort_key"])

        ordered = sorted(groups.values(), key=_sort_key)

        # The single lesson whose spell_date is the soonest one on or after
        # today - the "coming up next" lesson a student should prepare for.
        # None if no lesson has a parseable, non-past date.
        today = date.today()
        upcoming_key = None
        upcoming_date = None
        for g in ordered:
            date_tuple = parse_spell_date(g["spell_date"])
            if not date_tuple:
                continue
            resolved = resolve_spell_date(date_tuple, today)
            if resolved is None or resolved < today:
                continue
            if upcoming_date is None or resolved < upcoming_date:
                upcoming_date = resolved
                upcoming_key = g["lesson_key"]

        # Word ids per tag (batched once, reused per lesson group)
        all_tag_ids = {tid for g in ordered for tid in g["tag_ids"]}
        word_ids_by_tag: Dict[int, List[int]] = {}
        for tag_id in all_tag_ids:
            links = self.session.exec(
                select(WordTagLink.word_id).where(WordTagLink.tag_id == tag_id)
            ).all()
            word_ids_by_tag[tag_id] = list(links)

        recorded_by_lesson: Dict[str, set] = {}
        for row in self.session.exec(
            select(CheckpointProgress).where(
                (CheckpointProgress.user_name == user.name)
                & (CheckpointProgress.subject == subject)
            )
        ).all():
            recorded_by_lesson.setdefault(row.lesson_key, set()).add(row.checkpoint_index)

        result = []
        first_incomplete_found = False
        for g in ordered:
            word_ids = set()
            for tid in g["tag_ids"]:
                word_ids.update(word_ids_by_tag.get(tid, []))
            word_count = len(word_ids)

            mastery_pct = 0.0
            state_by_word = {}
            if word_ids:
                states = self.session.exec(
                    select(ReviewState).where(
                        (ReviewState.user_name == user.name)
                        & (ReviewState.word_id.in_(word_ids))
                    )
                ).all()
                state_by_word = {s.word_id: s for s in states}
                total = 0.0
                for wid in word_ids:
                    st = state_by_word.get(wid)
                    reps = st.repetitions if st else 0
                    total += min(reps, self._MASTERY_REPS) / self._MASTERY_REPS
                mastery_pct = total / word_count

            checkpoint_chunks = chunk_word_ids(sorted(word_ids))
            checkpoint_count = len(checkpoint_chunks)
            recorded = recorded_by_lesson.get(g["lesson_key"], set())
            passed = passed_checkpoint_indices(checkpoint_chunks, state_by_word, recorded)
            checkpoint_index = current_checkpoint_index(checkpoint_count, passed)
            all_points_passed = checkpoint_count > 0 and len(passed) == checkpoint_count
            # The review node counts as passed once a review session was
            # completed, or for a lesson whose words are all already
            # mastered (progress made before review nodes existed).
            review_passed = all_points_passed and (
                REVIEW_CHECKPOINT_INDEX in recorded
                or all(is_word_mastered(state_by_word.get(wid)) for wid in word_ids)
            )
            review_due_count = sum(
                1 for wid in word_ids
                if wid in state_by_word
                and (state_by_word[wid].due_date or today) <= today
            )

            if review_passed:
                status = "completed"
            elif not first_incomplete_found:
                status = "current"
                first_incomplete_found = True
            else:
                status = "locked"

            stars = (
                3 if mastery_pct >= 1.0 else
                2 if mastery_pct >= 0.5 else
                1 if mastery_pct > 0 else 0
            )

            result.append({
                "lesson_key": g["lesson_key"],
                "display_name": g["display_name"],
                "label_type": g["label_type"],
                "tags": g["tags"],
                "skills": g["skills"],
                "word_count": word_count,
                "mastery_pct": round(mastery_pct, 3),
                "stars": stars,
                "status": status,
                "spell_date": g["spell_date"],
                "is_upcoming": g["lesson_key"] == upcoming_key,
                "checkpoint_index": checkpoint_index,
                "checkpoint_count": checkpoint_count,
                "checkpoints": [
                    {"index": i, "word_ids": chunk, "passed": i in passed}
                    for i, chunk in enumerate(checkpoint_chunks)
                ],
                "review_passed": review_passed,
                "review_due_count": review_due_count,
            })

        return result
