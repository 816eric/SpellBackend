"""Idempotent seed script for MOE (Singapore) curriculum Chinese character
word cards, covering ALL grades P1-P6.

This is the generalized successor to the P1-only database/seed_moe_p1.py
(kept as-is and reused here for its LESSONS/PINYIN_MEANING data - don't
duplicate/edit character data in two places). P2-P6 data/glosses live in
database/moe_data_p2_p6.py. Both grades' groups share the same insert/tag
logic in database/moe_seed_lib.py.

Safe to re-run any number of times (checks for existing rows/tags/links
before inserting - see moe_seed_lib.seed_grade for details). This is also
what src.db_session.init_db() calls on every backend startup via
seed_all_moe_words(), so a fresh production DB gets populated automatically
on deploy with no manual step required.

Run standalone: .venv/bin/python database/seed_moe_words.py [grade]
(grade optional - defaults to seeding all of P1-P6)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, create_engine

from database.moe_seed_lib import seed_grade
from database import seed_moe_p1
from database.moe_data_p2_p6 import GRADE_LESSONS, PINYIN_MEANING, CJK_LESSON_NUM

DB_PATH = Path(__file__).resolve().parent / "db.sqlite3"

ALL_GRADES = ["P1", "P2", "P3", "P4", "P5", "P6"]


def seed_all_moe_words(session: Session, grades=None):
    """Seeds MOE word cards for the given grades (default: all of P1-P6)
    into the given session. Returns a dict {grade: (word_count, link_count,
    missing_pinyin)}. Idempotent - safe to call on every app startup."""
    grades = grades or ALL_GRADES
    results = {}
    for grade in grades:
        if grade == "P1":
            lessons = seed_moe_p1.LESSONS
            pinyin_meaning = seed_moe_p1.PINYIN_MEANING
            cjk = seed_moe_p1.CJK_LESSON_NUM
        else:
            lessons = GRADE_LESSONS[grade]
            pinyin_meaning = PINYIN_MEANING
            cjk = CJK_LESSON_NUM
        results[grade] = seed_grade(session, grade, lessons, pinyin_meaning, cjk)
    return results


def main():
    grade_arg = sys.argv[1].upper() if len(sys.argv) > 1 else None
    grades = [grade_arg] if grade_arg else ALL_GRADES

    engine = create_engine(f"sqlite:///{DB_PATH}")
    with Session(engine) as session:
        results = seed_all_moe_words(session, grades)

    total_words = 0
    total_links = 0
    for grade, (word_count, link_count, missing_pinyin) in results.items():
        print(f"{grade}: new words={word_count}, new links={link_count}"
              + (f", MISSING PINYIN={sorted(set(missing_pinyin))}" if missing_pinyin else ""))
        total_words += word_count
        total_links += link_count
    print(f"TOTAL: new words={total_words}, new links={total_links}")


if __name__ == "__main__":
    main()
