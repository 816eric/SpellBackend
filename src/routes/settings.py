import json
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.db_session import get_session_dep
from src.models.setting import UserSetting
from src.services.setting_manager import SettingManager

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/{user_id}", response_model=UserSetting)
def get_settings(user_id: int, session: Session = Depends(get_session_dep)):
    if spelling_prefs is not None:
        try:
            ok = isinstance(json.loads(spelling_prefs), dict) and len(spelling_prefs) <= 20000
        except ValueError:
            ok = False
        if not ok:
            raise HTTPException(status_code=400, detail="spelling_prefs must be a JSON object")
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
    moe_grade: str = None,
    moe_lessons: str = None,
    spelling_prefs: str = None,
    session: Session = Depends(get_session_dep)
):
    if num_study_words is not None and (not isinstance(num_study_words, int) or num_study_words < 1):
        raise HTTPException(status_code=400, detail="num_study_words must be a positive integer")
    if spell_repeat_count is not None and (not isinstance(spell_repeat_count, int) or spell_repeat_count < 1):
        raise HTTPException(status_code=400, detail="spell_repeat_count must be a positive integer")
    if study_words_source and study_words_source not in ["ALL_TAGS", "CURRENT_TAG"]:
        raise HTTPException(status_code=400, detail="study_words_source must be 'ALL_TAGS' or 'CURRENT_TAG'")
    if moe_grade and moe_grade.upper() not in ["P1", "P2", "P3", "P4", "P5", "P6"]:
        raise HTTPException(status_code=400, detail="moe_grade must be P1-P6")
    if moe_lessons is not None:
        try:
            parsed = json.loads(moe_lessons)
            ok = isinstance(parsed, dict) and all(
                isinstance(v, list) and all(isinstance(k, str) for k in v) for v in parsed.values()
            )
        except ValueError:
            ok = False
        if not ok or len(moe_lessons) > 20000:
            raise HTTPException(status_code=400, detail="moe_lessons must be a JSON object of grade -> list of lesson keys")
    manager = SettingManager(session)
    setting = manager.update_user_setting(user_id, study_words_source, num_study_words, spell_repeat_count, moe_grade.upper() if moe_grade else None, moe_lessons, spelling_prefs)
    return setting
