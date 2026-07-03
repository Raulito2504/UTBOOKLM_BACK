import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Exam, ExamAttempt, ExamQuestion, Flashcard, FlashcardDeck
from src.models import FlashcardDifficulty, ExamQuestionType


async def create_deck(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    document_id: uuid.UUID | None = None,
) -> FlashcardDeck:
    deck = FlashcardDeck(
        user_id=user_id,
        document_id=document_id,
        name=name,
    )
    db.add(deck)
    await db.flush()
    return deck


async def list_decks_by_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[FlashcardDeck]:
    result = await db.execute(
        select(FlashcardDeck)
        .where(FlashcardDeck.user_id == user_id)
        .order_by(FlashcardDeck.created_at.desc()),
    )
    return list(result.scalars().all())


async def create_flashcard(
    db: AsyncSession,
    *,
    deck_id: uuid.UUID,
    question: str,
    answer: str,
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM,
) -> Flashcard:
    flashcard = Flashcard(
        deck_id=deck_id,
        question=question,
        answer=answer,
        difficulty=difficulty,
    )
    db.add(flashcard)
    await db.flush()
    return flashcard


async def list_flashcards_by_deck(
    db: AsyncSession,
    *,
    deck_id: uuid.UUID,
) -> list[Flashcard]:
    result = await db.execute(
        select(Flashcard)
        .where(Flashcard.deck_id == deck_id)
        .order_by(Flashcard.created_at),
    )
    return list(result.scalars().all())


async def create_exam(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    document_id: uuid.UUID | None = None,
) -> Exam:
    exam = Exam(user_id=user_id, title=title, document_id=document_id)
    db.add(exam)
    await db.flush()
    return exam


async def create_exam_question(
    db: AsyncSession,
    *,
    exam_id: uuid.UUID,
    question_type: ExamQuestionType,
    prompt: str,
    options: dict | None = None,
    correct_answer: str | None = None,
    explanation: str | None = None,
) -> ExamQuestion:
    question = ExamQuestion(
        exam_id=exam_id,
        question_type=question_type,
        prompt=prompt,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation,
    )
    db.add(question)
    await db.flush()
    return question


async def create_exam_attempt(
    db: AsyncSession,
    *,
    exam_id: uuid.UUID,
    user_id: uuid.UUID,
    answers: dict,
    score: float | None = None,
    feedback: dict | None = None,
) -> ExamAttempt:
    attempt = ExamAttempt(
        exam_id=exam_id,
        user_id=user_id,
        answers=answers,
        score=score,
        feedback=feedback,
    )
    db.add(attempt)
    await db.flush()
    return attempt
