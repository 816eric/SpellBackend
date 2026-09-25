"""MOE (Singapore Ministry of Education) curriculum word cards.

Serves Primary 1-6 Chinese characters (see database/seed_moe_p1.py and
database/moe_data_p2_p6.py for the seed data, database/seed_moe_words.py
for the shared seeding logic, and the tag scheme below). An unrecognized
grade returns an empty lesson list (not an error) so the frontend can show
a graceful "coming soon" state.
"""
import re
from typing import Optional
from fastapi import APIRouter
from sqlmodel import select

from src.db_session import get_session
from src.models.tag import Tag
from src.models.link import WordTagLink
from src.models.word import SpellingWord
from src.models.history import StudyHistory

router = APIRouter(prefix="/moe-words", tags=["MOE Word Cards"])

# "MOE::P1::上::第一课" -> ("P1", "上", "第一课")
_LESSON_TAG_RE = re.compile(r"^MOE::(P\d+)::(上|下)::(第[一二三四五六七八九十]+课)$")
SUPPORTED_GRADES = {"P1", "P2", "P3", "P4", "P5", "P6"}

_CJK_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
            "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12, "十三": 13,
            "十四": 14, "十五": 15, "十六": 16, "十七": 17, "十八": 18, "十九": 19}


def _lesson_sort_key(term: str, lesson_name: str):
    num_str = lesson_name.replace("第", "").replace("课", "")
    num = _CJK_NUM.get(num_str, 999)
    term_order = 0 if term == "上" else 1
    return (term_order, num)


@router.get("")
def get_moe_words(grade: str = "P1", user_name: Optional[str] = None):
    """Returns MOE curriculum lessons with characters grouped by lesson,
    each with pinyin, meaning, whether it's write-required (识写字), and
    the requesting user's practiced_count (0 if never studied)."""
    grade = (grade or "").upper()
    if grade not in SUPPORTED_GRADES:
        return {"grade": grade, "supported": False, "lessons": []}

    with get_session() as session:
        all_tags = session.exec(
            select(Tag).where(Tag.label_type == "MOE")
        ).all()

        write_tag_name = f"MOE::{grade}::写字"
        write_tag = next((t for t in all_tags if t.tag == write_tag_name), None)
        write_word_ids = set()
        if write_tag:
            write_word_ids = set(
                session.exec(
                    select(WordTagLink.word_id).where(WordTagLink.tag_id == write_tag.id)
                ).all()
            )

        lesson_tags = []
        for t in all_tags:
            m = _LESSON_TAG_RE.match(t.tag)
            if not m or m.group(1) != grade:
                continue
            lesson_tags.append((t, m.group(2), m.group(3)))

        lesson_tags.sort(key=lambda x: _lesson_sort_key(x[1], x[2]))

        # Practice counts for this user, if given.
        counts_by_word = {}
        if user_name:
            hist_rows = session.exec(
                select(StudyHistory).where(StudyHistory.user_name == user_name.upper())
            ).all()
            counts_by_word = {h.word_id: h.count for h in hist_rows}

        lessons = []
        for tag, term, lesson_name in lesson_tags:
            word_ids = session.exec(
                select(WordTagLink.word_id).where(WordTagLink.tag_id == tag.id)
            ).all()
            if not word_ids:
                continue
            words = session.exec(
                select(SpellingWord).where(SpellingWord.id.in_(word_ids))
            ).all()
            characters = [
                {
                    "id": w.id,
                    "text": w.text,
                    "pinyin": w.pinyin,
                    "meaning": w.meaning,
                    "write_required": w.id in write_word_ids,
                    "practiced_count": counts_by_word.get(w.id, 0),
                }
                for w in words
            ]
            lessons.append({
                "lesson_key": tag.tag,
                "term": term,
                "display_name": lesson_name,
                "characters": characters,
            })

        return {
            "grade": grade,
            "supported": True,
            "user_name": user_name.upper() if user_name else None,
            "lessons": lessons,
        }
