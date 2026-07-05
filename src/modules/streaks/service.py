from datetime import datetime


def empty_streak_summary() -> dict[str, int]:
    return {
        "current_streak": 0,
        "longest_streak": 0,
        "total_active_days": 0,
    }


def normalize_activity_date(activity_date: datetime | None) -> datetime:
    return activity_date or datetime.now()
