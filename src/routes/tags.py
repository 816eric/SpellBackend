
from fastapi import APIRouter, HTTPException, Body, Request
from src.security import require_admin
from typing import List
from ..services.tag_manager import TagManager
from ..models.tag import Tag
from ..models.user import User
from sqlmodel import select
from ..db_session import get_session


# ...existing code...
router = APIRouter(prefix="/tags", tags=["Tags"])
# Unassign multiple tags from a user
@router.post("/user/{user_name}/unassign")
def unassign_multiple_tags_from_user(user_name: str, tag_ids: list[int] = Body(...)):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        results = []
        for tag_id in tag_ids:
            TagManager.unassign_tag_from_user(user.id, tag_id)
            results.append({"tag_id": tag_id})
        return {"success": True, "unassigned": results}
    
# Assign multiple tags to a user
@router.post("/user/{user_name}/assign")
def assign_multiple_tags_to_user(user_name: str, tag_ids: list[int] = Body(...)):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        results = []
        for tag_id in tag_ids:
            link = TagManager.assign_tag_to_user(user.id, tag_id)
            results.append({"tag_id": tag_id, "link_id": link.id})
        return {"success": True, "assigned": results}

# Assign an existing tag to a user
@router.post("/user/{user_name}/assign/{tag_id}")
def assign_tag_to_user(user_name: str, tag_id: int):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        link = TagManager.assign_tag_to_user(user.id, tag_id)
        return {"success": True, "link_id": link.id}

# Unassign a tag from a user
@router.post("/user/{user_name}/unassign/{tag_id}")
def unassign_tag_from_user(user_name: str, tag_id: int):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        TagManager.unassign_tag_from_user(user.id, tag_id)
        return {"success": True}

# Delete a tag (owner only)
@router.delete("/user/{user_name}/delete/{tag_id}")
def delete_tag(user_name: str, tag_id: int):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = TagManager.delete_tag(user.id, tag_id)
        if not result:
            raise HTTPException(status_code=403, detail="Only the owner can delete this tag.")
        return {"success": True}

# Edit a tag (owner only)
@router.put("/user/{user_name}/edit/{tag_id}", response_model=Tag)
def edit_tag(user_name: str, tag_id: int, new_tag: str, new_description: str = ""):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        tag = TagManager.edit_tag(user.id, tag_id, new_tag, new_description)
        if not tag:
            raise HTTPException(status_code=403, detail="Only the owner can edit this tag.")
        return tag



@router.get("/user/{user_name}", response_model=List[Tag])
def get_user_tags(user_name: str):
    # Get tags for the specified user (including ADMIN)
    user_name_upper = user_name.upper() if user_name else None
    
    with get_session() as session:
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            return []
        return TagManager.get_tags_by_user(user.id)
    
# Get all tags
@router.get("/all", response_model=List[Tag])
def get_all_tags():
    return TagManager.get_all_tags()


# Get available tags for a user (admin tags + user's own tags)
@router.get("/available/{user_name}", response_model=List[Tag])
def get_available_tags_for_user(user_name: str):
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            # If user not found, still return admin tags (for guest users)
            return TagManager.get_available_tags_for_user(0)
        return TagManager.get_available_tags_for_user(user.id)


# Set a tag's spell_date (free text - lesson/dictation scheduled date,
# as printed on the source worksheet; may be non-ISO, e.g. Chinese
# numerals). No HTTP route previously existed for this - it could only be
# set via JSON import (WordManager.add_word's spell_date param) run
# against a local DB, which production has no direct access to.
@router.put("/{tag_id}/spell-date", response_model=Tag)
def set_tag_spell_date(tag_id: int, request: Request, spell_date: str = Body(..., embed=True)):
    require_admin(request)  # lesson schedule is operator-managed
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        tag.spell_date = spell_date
        session.add(tag)
        session.commit()
        session.refresh(tag)
        return tag


@router.post("/user/{user_name}/create", response_model=Tag)
def create_user_tag(user_name: str, tag: Tag):
    #convert tag to upper case
    tag.tag = tag.tag.upper()
    with get_session() as session:
        user_name_upper = user_name.upper() if user_name else None
        user = session.exec(select(User).where(User.name == user_name_upper)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return TagManager.create_tag(tag=tag.tag, created_by=str(user.id), description=tag.description or "")


