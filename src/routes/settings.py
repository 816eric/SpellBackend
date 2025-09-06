from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.db_session import get_session
from src.models.setting import UserSetting
from src.services.setting_manager import SettingManager

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/{user_id}", response_model=UserSetting)
def get_settings(user_id: int, session: Session = Depends(get_session)):
    manager = SettingManager(session)
    setting = manager.get_user_setting(user_id)
    if not setting:
        raise HTTPException(status_code=404, detail="Settings not found for user")
    return setting

@router.post("/{user_id}", response_model=UserSetting)
def update_settings(
    user_id: int,
    study_words_source: str = None,
    num_study_words: int = None,
    spell_repeat_count: int = None,
    session: Session = Depends(get_session)
):
    if num_study_words is not None and (not isinstance(num_study_words, int) or num_study_words < 1):
        raise HTTPException(status_code=400, detail="num_study_words must be a positive integer")
    if spell_repeat_count is not None and (not isinstance(spell_repeat_count, int) or spell_repeat_count < 1):
        raise HTTPException(status_code=400, detail="spell_repeat_count must be a positive integer")
    if study_words_source and study_words_source not in ["ALL_TAGS", "CURRENT_TAG"]:
        raise HTTPException(status_code=400, detail="study_words_source must be 'ALL_TAGS' or 'CURRENT_TAG'")
    manager = SettingManager(session)
    setting = manager.update_user_setting(user_id, study_words_source, num_study_words, spell_repeat_count)
    return setting
