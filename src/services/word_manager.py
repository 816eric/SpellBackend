from sqlmodel import Session, select
from src.models.word import SpellingWord
import json
from typing import IO

class WordManager:
    def __init__(self, session: Session):
        self.session = session

    def add_word(self, word: SpellingWord):
        self.session.add(word)
        self.session.commit()
        return word

    def get_words_by_user_and_tags(self, user: str, tags: list[str]):
        query = select(SpellingWord).where(
            (SpellingWord.created_by == "admin") | (SpellingWord.created_by == user)
        )
        for tag in tags:
            query = query.where(SpellingWord.tags.contains(tag))
        return self.session.exec(query).all()

    def import_words_from_json(self, file: IO, created_by: str = "admin", language: str = "other"):
        data = json.load(file)
        words_to_add = {}
        for tag, word_list in data.items():
            for word in word_list:
                # Use (word, tag) as key to avoid duplicates for same word/tag
                words_to_add[(word, tag)] = {
                    "text": word,
                    "language": language,
                    "created_by": created_by,
                    "is_personal": False,
                    "tags": tag
                }
        for word_info in words_to_add.values():
            spelling_word = SpellingWord(**word_info)
            self.session.add(spelling_word)
        self.session.commit()
        return len(words_to_add)

    def get_tags_by_user(self, user: str):
        query = select(SpellingWord.tags).where(
            (SpellingWord.created_by == "admin") | (SpellingWord.created_by == user)
        )
        tags = set()
        for tag in self.session.exec(query):
            if tag:
                tags.add(tag)
        return list(tags)