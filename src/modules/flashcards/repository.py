import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Flashcard, FlashcardDeck, FlashcardDifficulty


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
