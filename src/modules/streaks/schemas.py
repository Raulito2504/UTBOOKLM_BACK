from datetime import datetime

from pydantic import BaseModel


class StudyActivityRequest(BaseModel):
    activity_type: str
    activity_date: datetime | None = None
    metadata_json: dict | None = None


class StreakSummary(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
