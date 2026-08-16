from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.services import difficulty

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/difficulty")
def get_current_difficulty(db: DBSession = Depends(get_db)) -> dict:
    """Read-only peek at the auto-computed difficulty, without creating a session."""
    profile = difficulty.get_or_create_profile(db)
    week = difficulty.current_week(profile.program_start_date)
    return {"difficulty": difficulty.get_difficulty(week), "week": week}
