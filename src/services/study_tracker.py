from sqlmodel import Session
from src.models.history import StudyHistory
from src.models.user import User
from src.models.reward import RewardHistory
from datetime import datetime

class StudyTracker:
    def __init__(self, session: Session):
        self.session = session

    def log_study(self, user_name: str, word_id: int):
        now = datetime.now()
        study = self.session.get(StudyHistory, (user_name, word_id))
        if study:
            study.count += 1
            study.last_studied_at = now
        else:
            study = StudyHistory(user_name=user_name, word_id=word_id, count=1, last_studied_at=now)
            self.session.add(study)

        user = self.session.get(User, user_name)
        user.total_points += 1

        reward = RewardHistory(user_name=user_name, action="earn", points=1, reason="study", timestamp=now)
        self.session.add(reward)

        self.session.commit()
        return study