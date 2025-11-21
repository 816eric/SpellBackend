from sqlmodel import Session, select
from datetime import datetime
from ..models.tag import Tag
from ..models.word import SpellingWord
from ..db_session import get_session
from ..models.link import UserTagsLink, WordTagLink



class TagManager:

    @staticmethod
    def get_all_tags():
        with get_session() as session:
            return session.exec(select(Tag)).all()

    @staticmethod
    def assign_tag_to_user(user_id: int, tag_id: int):
        """Assign an existing tag to a user (create UserTagsLink if not present)."""
        with get_session() as session:
            link = session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user_id, UserTagsLink.tag_id == tag_id)).first()
            if not link:
                link = UserTagsLink(user_id=user_id, tag_id=tag_id)
                session.add(link)
                session.commit()
                session.refresh(link)
            return link

    @staticmethod
    def unassign_tag_from_user(user_id: int, tag_id: int):
        """Unassign a tag from a user (remove UserTagsLink)."""
        with get_session() as session:
            link = session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user_id, UserTagsLink.tag_id == tag_id)).first()
            if link:
                session.delete(link)
                session.commit()
            return True

    @staticmethod
    def delete_tag(user_id: int, tag_id: int):
        """Delete a tag. Only the owner can delete. If others use it, set owner to 'admin'. If not, remove tag and all WordTagLink."""
        with get_session() as session:
            tag = session.get(Tag, tag_id)
            if not tag:
                return False
            if str(tag.created_by) != str(user_id):
                return False  # Only owner can delete
            # Remove UserTagsLink for this user/tag
            user_tag_link = session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user_id, UserTagsLink.tag_id == tag_id)).first()
            if user_tag_link:
                session.delete(user_tag_link)
                session.commit()
            # Check if other users still use this tag
            other_links = session.exec(select(UserTagsLink).where(UserTagsLink.tag_id == tag_id)).all()
            if other_links:
                tag.created_by = "admin"
                session.add(tag)
                session.commit()
            else:
                # Remove all WordTagLink for this tag
                word_links = session.exec(select(WordTagLink).where(WordTagLink.tag_id == tag_id)).all()
                for wl in word_links:
                    session.delete(wl)
                session.delete(tag)
                session.commit()
            return True

    @staticmethod
    def edit_tag(user_id: int, tag_id: int, new_tag: str, new_description: str = ""):
        """Edit tag info. Only owner can edit."""
        with get_session() as session:
            tag = session.get(Tag, tag_id)
            if not tag:
                return None
            if str(tag.created_by) != str(user_id):
                return None
            tag.tag = new_tag
            tag.description = new_description
            session.add(tag)
            session.commit()
            session.refresh(tag)
            return tag

    @staticmethod
    def create_tag(tag: str, created_by: str, description: str = "") -> Tag:
        with get_session() as session:
            existing = session.exec(select(Tag).where(Tag.tag == tag, Tag.created_by == created_by)).first()
            if existing:
                return existing
            tag_obj = Tag(tag=tag, created_by=created_by, description=description)
            session.add(tag_obj)
            session.commit()
            session.refresh(tag_obj)
            # Owner automatically gets UserTagsLink
            user_id = None
            try:
                user_id = int(created_by)
            except Exception:
                pass
            if user_id:
                link = session.exec(select(UserTagsLink).where(UserTagsLink.user_id == user_id, UserTagsLink.tag_id == tag_obj.id)).first()
                if not link:
                    session.add(UserTagsLink(user_id=user_id, tag_id=tag_obj.id))
                    session.commit()
            return tag_obj

    @staticmethod
    # assign_tag_to_word is no longer needed

    @staticmethod
    def get_tags_by_user(user_id: int):
        with get_session() as session:
            tag_ids = list(session.exec(select(UserTagsLink.tag_id).where(UserTagsLink.user_id == user_id)).all())
            if not tag_ids:
                return []
            tags = session.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()
            return tags

