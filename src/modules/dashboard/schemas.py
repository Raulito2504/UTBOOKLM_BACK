from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentMetrics(BaseModel):
    total: int
    ready: int
    processing: int
    failed: int


class ChatMetrics(BaseModel):
    total: int
    messages: int


class FlashcardMetrics(BaseModel):
    decks: int
    cards: int
    reviewed: int


class QuizMetrics(BaseModel):
    total: int
    attempts: int
    average_score: float | None = None


class ActivityMetrics(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int


class DashboardMetricsResponse(BaseModel):
    documents: DocumentMetrics
    chats: ChatMetrics
    flashcards: FlashcardMetrics
    quizzes: QuizMetrics
    activity: ActivityMetrics


class DashboardActivityResponse(BaseModel):
    id: UUID
    user_id: UUID
    activity_type: str
    activity_date: datetime
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotebookCardResponse(BaseModel):
    id: UUID
    title: str
    source_count: int
    created_at: datetime
    updated_at: datetime

