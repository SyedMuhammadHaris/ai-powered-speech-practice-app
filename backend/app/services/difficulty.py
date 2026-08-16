from datetime import date

from sqlalchemy.orm import Session as DBSession

from app.models import Profile

VALID_DIFFICULTIES = ("beginner", "intermediate", "advanced")


def get_difficulty(week: int) -> str:
    """Map a program week number to a difficulty level.

    Week 1 -> beginner, weeks 2-3 -> intermediate, week 4+ -> advanced.
    """
    if week == 1:
        return "beginner"
    elif week in (2, 3):
        return "intermediate"
    else:
        return "advanced"


def current_week(program_start_date: date, today: date | None = None) -> int:
    """Compute the 1-indexed program week for a given start date."""
    today = today or date.today()
    return (today - program_start_date).days // 7 + 1


def get_or_create_profile(db: DBSession) -> Profile:
    """Fetch the single v1 profile row, creating it (starting today) on first use."""
    profile = db.query(Profile).first()
    if profile is None:
        profile = Profile(program_start_date=date.today())
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
