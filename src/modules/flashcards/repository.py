import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamQuestionType,
    Flashcard,
    FlashcardDeck,
    FlashcardDifficulty,
    StudyProgress,
)


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
    limit: int = 20,
    offset: int = 0,
) -> list[FlashcardDeck]:
    result = await db.execute(
        select(FlashcardDeck)
        .where(FlashcardDeck.user_id == user_id)
        .order_by(FlashcardDeck.created_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def get_deck_by_user(
    db: AsyncSession,
    *,
    deck_id: uuid.UUID,
    user_id: uuid.UUID,
) -> FlashcardDeck | None:
    result = await db.execute(
        select(FlashcardDeck).where(
            FlashcardDeck.id == deck_id,
            FlashcardDeck.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def update_deck_card_count(
    db: AsyncSession,
    *,
    deck: FlashcardDeck,
    card_count: int,
) -> FlashcardDeck:
    deck.card_count = card_count
    await db.flush()
    return deck


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


async def get_flashcard_by_user(
    db: AsyncSession,
    *,
    flashcard_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Flashcard | None:
    result = await db.execute(
        select(Flashcard)
        .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
        .where(
            Flashcard.id == flashcard_id,
            FlashcardDeck.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def create_study_progress(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    flashcard_id: uuid.UUID,
) -> StudyProgress:
    result = await db.execute(
        select(StudyProgress).where(
            StudyProgress.user_id == user_id,
            StudyProgress.flashcard_id == flashcard_id,
        ),
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = StudyProgress(user_id=user_id, flashcard_id=flashcard_id)
        db.add(progress)
    else:
        progress.last_reviewed = datetime.now(timezone.utc)
    await db.flush()
    return progress


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


async def list_exams_by_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[Exam]:
    result = await db.execute(
        select(Exam)
        .where(Exam.user_id == user_id)
        .order_by(Exam.created_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def get_exam_by_user(
    db: AsyncSession,
    *,
    exam_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Exam | None:
    result = await db.execute(
        select(Exam).where(
            Exam.id == exam_id,
            Exam.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


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


async def list_exam_questions(
    db: AsyncSession,
    *,
    exam_id: uuid.UUID,
) -> list[ExamQuestion]:
    result = await db.execute(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.created_at),
    )
    return list(result.scalars().all())


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


async def list_exam_attempts_by_user(
    db: AsyncSession,
    *,
    exam_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[ExamAttempt]:
    result = await db.execute(
        select(ExamAttempt)
        .where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.user_id == user_id,
        )
        .order_by(ExamAttempt.created_at.desc()),
    )
    return list(result.scalars().all())
