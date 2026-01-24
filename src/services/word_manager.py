from sqlmodel import Session, select
from src.models.word import SpellingWord
from src.models.tag import Tag
from src.models.link import WordTagLink, UserTagsLink
import json
from typing import IO
from src.models.user import User

class WordManager:

    def __init__(self, session: Session):
        self.session = session

    def add_word(self, word: SpellingWord, tag: str = None, user_id: int = None, is_public: bool = False):
        print(f"Adding word: {word.text}, tag: {tag}, user_id: {user_id}, is_public: {is_public}")
        # Add word if not exist
        existing_word = self.session.exec(select(SpellingWord).where(SpellingWord.text == word.text)).first()
        if not existing_word:
            self.session.add(word)
            self.session.commit()
            word_id = word.id
        else:
            word_id = existing_word.id
        tag_id = None
        if tag:
            # Add tag if not exist
            tag_obj = self.session.exec(select(Tag).where(Tag.tag == tag)).first()
            if not tag_obj:
                tag_obj = Tag(tag=tag, created_by=user_id or "admin")
                self.session.add(tag_obj)
                self.session.commit()
            tag_id = tag_obj.id
            # Add UserTagsLink if not exist
            if user_id:
                user_tag_link = self.session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user_id, UserTagsLink.tag_id == tag_id)).first()
                if not user_tag_link:
                    self.session.add(UserTagsLink(user_id=user_id, tag_id=tag_id))
            
            # If public tag, also link to ADMIN user (user_id = 1)
            if is_public:
                admin_user = self.session.exec(select(User).where(User.name == "ADMIN")).first()
                if admin_user:
                    admin_tag_link = self.session.exec(select(UserTagsLink).where(UserTagsLink.user_id == admin_user.id, UserTagsLink.tag_id == tag_id)).first()
                    if not admin_tag_link:
                        self.session.add(UserTagsLink(user_id=admin_user.id, tag_id=tag_id))
            
            # Add WordTagLink if not exist
            word_tag_link = self.session.exec(select(WordTagLink).where(WordTagLink.word_id == word_id, WordTagLink.tag_id == tag_id)).first()
            if not word_tag_link:
                self.session.add(WordTagLink(word_id=word_id, tag_id=tag_id))
        self.session.commit()
        return self.session.get(SpellingWord, word_id)

    def get_words_by_user_and_tags(self, user_id: int, tags: list[str]):
        # Get all words for this user and tags
        if not tags:
            # Return all words created by user
            return self.session.exec(select(SpellingWord).where(SpellingWord.created_by == user_id)).all()
        tag_ids = list(self.session.exec(select(Tag.id).where(Tag.tag.in_(tags))).all())
        word_ids = set()
        for tag_id in tag_ids:
            links = self.session.exec(select(WordTagLink.word_id).where(WordTagLink.tag_id == tag_id)).all()
            word_ids.update(links)
        if not word_ids:
            return []
        return self.session.exec(select(SpellingWord).where(SpellingWord.id.in_(word_ids))).all()

    def get_all_words_for_user(self, user_id: int):
        # Get all tag ids linked to the user
        tag_ids = list(self.session.exec(select(UserTagsLink.tag_id).where(UserTagsLink.user_id == user_id)).all())
        if not tag_ids:
            return []
        # Get all word ids linked to those tags
        word_ids = set()
        for tag_id in tag_ids:
            links = self.session.exec(select(WordTagLink.word_id).where(WordTagLink.tag_id == tag_id)).all()
            word_ids.update(links)
        if not word_ids:
            return []
        # Return all words with those ids
        return self.session.exec(select(SpellingWord).where(SpellingWord.id.in_(word_ids))).all()

    def import_words_from_json(self, file: IO, created_by: str = "admin", language: str = "other"):
        import re
        data = json.load(file)
        count = 0
        def detect_language(word_text: str) -> str:
            # Simple heuristics for language detection
            if re.search(r'[\u4e00-\u9fff]', word_text):
                return "chinese"
            elif re.search(r'[\u3040-\u30ff]', word_text):
                return "japanese"
            elif re.search(r'[\uac00-\ud7af]', word_text):
                return "korean"
            elif re.search(r'[A-Za-z\-\' ]+', word_text):
                return "english"
            else:
                return language
        # Ensure 'admin' user exists and get id if created_by is 'admin'
        admin_user_id = None
        if created_by == "admin" or created_by.upper() == "ADMIN":
            admin_user = self.session.exec(select(User).where(User.name == "ADMIN")).first()
            if not admin_user:
                admin_user = User(name="ADMIN")
                self.session.add(admin_user)
                self.session.commit()
            admin_user_id = admin_user.id
        for tag, word_list in data.items():
            for word_text in word_list:
                lang = detect_language(word_text)
                # Always use user_id (admin's id if admin, else created_by)
                if created_by == "admin":
                    word = SpellingWord(text=word_text, language=lang, created_by=admin_user_id)
                    self.add_word(word, tag=tag, user_id=admin_user_id)
                else:
                    word = SpellingWord(text=word_text, language=lang, created_by=created_by)
                    self.add_word(word, tag=tag, user_id=created_by)
                count += 1
        return count

    def get_tags_by_user(self, user_id: int):
        tag_ids = [row[0] for row in self.session.exec(select(UserTagsLink.tag_id).where(UserTagsLink.user_id == user_id)).all()]
        if not tag_ids:
            return []
        tags = self.session.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()
        return tags
    
    # get_user_words is now handled by get_words_by_user_and_tags