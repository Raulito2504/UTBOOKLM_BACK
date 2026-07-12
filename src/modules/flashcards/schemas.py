from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.models import ExamQuestionType, FlashcardDifficulty


class FlashcardDraft(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM


class FlashcardPayload(BaseModel):
    flashcards: list[FlashcardDraft] = Field(..., min_length=1)


class FlashcardGenerateRequest(BaseModel):
    document_ids: list[UUID] = Field(..., min_length=1, max_length=10)
    count: int = Field(10, ge=1, le=50)
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM
    deck_name: str | None = Field(None, min_length=1, max_length=255)


class FlashcardDeckResponse(BaseModel):
    id: UUID
    name: str
    document_id: UUID | None = None
    card_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FlashcardResponse(BaseModel):
    id: UUID
    deck_id: UUID
    question: str
    answer: str
    difficulty: FlashcardDifficulty
    created_at: datetime

    model_config = {"from_attributes": True}


class FlashcardReviewRequest(BaseModel):
    remembered: bool | None = None


class FlashcardReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    flashcard_id: UUID
    last_reviewed: datetime

    model_config = {"from_attributes": True}


class ExamQuestionDraft(BaseModel):
    question_type: ExamQuestionType
    prompt: str = Field(..., min_length=1)
    options: dict[str, str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    @model_validator(mode="after")
    def validate_question_shape(self) -> "ExamQuestionDraft":
        if self.question_type == ExamQuestionType.MULTIPLE_CHOICE:
            if not self.options or len(self.options) < 2:
                raise ValueError("multiple_choice questions require options")
            if self.correct_answer not in self.options:
                raise ValueError("multiple_choice correct_answer must match an option")
        if self.question_type == ExamQuestionType.TRUE_FALSE:
            normalized = (self.correct_answer or "").lower()
            if normalized not in {"true", "false"}:
                raise ValueError("true_false correct_answer must be true or false")
            self.correct_answer = normalized
        if self.question_type == ExamQuestionType.OPEN and not self.correct_answer:
            raise ValueError("open questions require an expected answer or rubric")
        return self


class QuizPayload(BaseModel):
    questions: list[ExamQuestionDraft] = Field(..., min_length=1)


class QuizGenerateRequest(BaseModel):
    document_ids: list[UUID] = Field(..., min_length=1, max_length=10)
    title: str | None = Field(None, min_length=1, max_length=255)
    question_count: int = Field(10, ge=1, le=50)
    question_types: list[ExamQuestionType] = Field(
        default_factory=lambda: [ExamQuestionType.MULTIPLE_CHOICE],
        min_length=1,
        max_length=3,
    )

    @field_validator("question_types")
    @classmethod
    def unique_question_types(
        cls,
        value: list[ExamQuestionType],
    ) -> list[ExamQuestionType]:
        return list(dict.fromkeys(value))


class QuizResponse(BaseModel):
    id: UUID
    title: str
    document_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizQuestionResponse(BaseModel):
    id: UUID
    exam_id: UUID
    question_type: ExamQuestionType
    prompt: str
    options: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizAnswerSubmitRequest(BaseModel):
    answers: dict[UUID, str] = Field(..., min_length=1)


class QuizAttemptResponse(BaseModel):
    id: UUID
    exam_id: UUID
    user_id: UUID
    answers: dict[str, Any]
    score: float | None = None
    feedback: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
