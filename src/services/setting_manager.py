from sqlmodel import Session, select
from src.models.setting import UserSetting

class SettingManager:
    def __init__(self, session: Session):
        self.session = session

    def get_user_setting(self, user_id: int) -> UserSetting:
        setting = self.session.exec(select(UserSetting).where(UserSetting.user_id == user_id)).first()
        return setting

    def update_user_setting(self, user_id: int, study_words_source: str = None, num_study_words: int = None, spell_repeat_count: int = None, moe_grade: str = None, moe_lessons: str = None, spelling_prefs: str = None) -> UserSetting:
        setting = self.get_user_setting(user_id)
        if not setting:
            setting = UserSetting(user_id=user_id)
            self.session.add(setting)
        if study_words_source:
            setting.study_words_source = study_words_source
        if num_study_words is not None:
            setting.num_study_words = num_study_words
        if spell_repeat_count is not None:
            setting.spell_repeat_count = spell_repeat_count
        if moe_grade:
            setting.moe_grade = moe_grade
        if moe_lessons is not None:
            setting.moe_lessons = moe_lessons
        if spelling_prefs is not None:
            setting.spelling_prefs = spelling_prefs
        self.session.commit()
        self.session.refresh(setting)
        return setting
