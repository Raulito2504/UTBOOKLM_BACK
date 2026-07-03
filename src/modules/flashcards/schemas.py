from uuid import UUID

from pydantic import BaseModel

from src.models import ExamQuestionType, FlashcardDifficulty


class FlashcardDraft(BaseModel):
    question: str
    answer: str
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM


class FlashcardGenerateRequest(BaseModel):
    document_ids: list[UUID]
    count: int = 10


class ExamQuestionDraft(BaseModel):
    question_type: ExamQuestionType
    prompt: str
    options: dict[str, str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
