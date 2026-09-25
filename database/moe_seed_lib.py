"""Shared, idempotent seeding logic for MOE (Singapore) curriculum Chinese
character word cards, used by every grade (P1-P6).

Generalized out of the original one-off database/seed_moe_p1.py so the
same insert/tag logic can run for P2-P6 too (see database/seed_moe_words.py)
and be called automatically on every backend startup (see
database/init_db.py) - safe to re-run any number of times: it looks up
existing SpellingWord rows by (text, language="chinese") and existing Tag
rows by tag string before inserting anything, and backfills pinyin/meaning
on words that already exist without it, rather than erroring or duplicating.

Tag scheme (unchanged from P1, extended per grade):
- One tag per lesson: "MOE::{grade}::{term}::第{cjk_num}课", label_type="MOE".
- One shared tag per grade: "MOE::{grade}::写字", label_type="MOE", linked to
  every character that appears in ANY lesson's 识写字 (write-required) list
  for that grade.
"""
from sqlmodel import Session, select

from src.models.word import SpellingWord
from src.models.tag import Tag
from src.models.link import WordTagLink


def seed_grade(session: Session, grade: str, lessons, pinyin_meaning: dict, cjk_lesson_num):
    """Seeds one grade's MOE lessons. `lessons` is a list of
    (term, lesson_number, read_str, write_str) tuples. `pinyin_meaning` maps
    character -> (pinyin, meaning). `cjk_lesson_num` maps lesson_number (int)
    -> Chinese numeral string (e.g. 1 -> "一").

    Returns (word_count, link_count, missing_pinyin) where word_count/
    link_count are the number of NEW rows created this call (0 on a no-op
    re-run) and missing_pinyin lists any characters with no pinyin/meaning
    entry (should be empty - a data bug if not).
    """
    write_tag_name = f"MOE::{grade}::写字"

    write_required_chars = set()
    for _, _, _, write_str in lessons:
        write_required_chars.update(write_str)

    write_tag = session.exec(select(Tag).where(Tag.tag == write_tag_name)).first()
    if not write_tag:
        write_tag = Tag(
            tag=write_tag_name,
            created_by="admin",
            description=f"Characters {grade} students must be able to write (识写字), not just recognize.",
            label_type="MOE",
        )
        session.add(write_tag)
        session.commit()
        session.refresh(write_tag)

    word_count = 0
    link_count = 0
    missing_pinyin = []

    for term, num, read_str, write_str in lessons:
        cjk_num = cjk_lesson_num[num]
        lesson_tag_name = f"MOE::{grade}::{term}::第{cjk_num}课"
        lesson_tag = session.exec(select(Tag).where(Tag.tag == lesson_tag_name)).first()
        if not lesson_tag:
            lesson_tag = Tag(
                tag=lesson_tag_name,
                created_by="admin",
                description=f"MOE {grade} {term} lesson {num} (第{cjk_num}课) characters.",
                label_type="MOE",
            )
            session.add(lesson_tag)
            session.commit()
            session.refresh(lesson_tag)

        write_set = set(write_str)
        for ch in read_str:
            pinyin, meaning = pinyin_meaning.get(ch, (None, None))
            if pinyin is None:
                missing_pinyin.append(ch)

            word = session.exec(
                select(SpellingWord).where(
                    (SpellingWord.text == ch) & (SpellingWord.language == "chinese")
                )
            ).first()
            if not word:
                word = SpellingWord(
                    text=ch,
                    language="chinese",
                    created_by="admin",
                    pinyin=pinyin,
                    meaning=meaning,
                )
                session.add(word)
                session.commit()
                session.refresh(word)
                word_count += 1
            else:
                changed = False
                if not word.pinyin and pinyin:
                    word.pinyin = pinyin
                    changed = True
                if not word.meaning and meaning:
                    word.meaning = meaning
                    changed = True
                if changed:
                    session.add(word)
                    session.commit()

            existing_link = session.exec(
                select(WordTagLink).where(
                    (WordTagLink.word_id == word.id) & (WordTagLink.tag_id == lesson_tag.id)
                )
            ).first()
            if not existing_link:
                session.add(WordTagLink(word_id=word.id, tag_id=lesson_tag.id))
                link_count += 1

            if ch in write_set:
                existing_write_link = session.exec(
                    select(WordTagLink).where(
                        (WordTagLink.word_id == word.id) & (WordTagLink.tag_id == write_tag.id)
                    )
                ).first()
                if not existing_write_link:
                    session.add(WordTagLink(word_id=word.id, tag_id=write_tag.id))
                    link_count += 1

        session.commit()

    return word_count, link_count, missing_pinyin
