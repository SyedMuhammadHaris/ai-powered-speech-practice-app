from datetime import datetime

from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    topic: str


class SessionStartResponse(BaseModel):
    session_id: str
    topic: str
    difficulty: str
    opening_line: str


class SessionEndResponse(BaseModel):
    session_id: str
    ended_at: datetime


class FeedbackResponse(BaseModel):
    session_id: str
    summary_text: str
    common_mistakes: list[str]
    vocab_suggestions: list[str]
