from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.core.exceptions import AppError
from src.modules.flashcards import service
from src.modules.flashcards.schemas import (
    FlashcardDeckResponse,
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    QuizAnswerSubmitRequest,
    QuizAttemptResponse,
    QuizGenerateRequest,
    QuizQuestionResponse,
    QuizResponse,
)


router = APIRouter()
decks_router = APIRouter()
quizzes_router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "flashcards", "status": "ready"}


@router.post(
    "/generate",
    response_model=FlashcardDeckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_flashcards(
    payload: FlashcardGenerateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> FlashcardDeckResponse:
    try:
        deck = await service.generate_flashcards(
            db,
            current_user=current_user,
            document_ids=payload.document_ids,
            count=payload.count,
            difficulty=payload.difficulty,
            deck_name=payload.deck_name,
        )
        await db.commit()
        await db.refresh(deck)
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    except service.GenerationDependencyError:
        await db.rollback()
        raise _generation_failed_error() from None
    except service.GeneratedPayloadInvalidError as exc:
        await db.rollback()
        raise _generated_payload_invalid_error(str(exc)) from None
    return FlashcardDeckResponse.model_validate(deck)


@decks_router.get("", response_model=list[FlashcardDeckResponse])
@router.get("/decks", response_model=list[FlashcardDeckResponse])
async def list_decks(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[FlashcardDeckResponse]:
    decks = await service.list_decks(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return [FlashcardDeckResponse.model_validate(deck) for deck in decks]


@decks_router.get("/{deck_id}", response_model=FlashcardDeckResponse)
@router.get("/decks/{deck_id}", response_model=FlashcardDeckResponse)
async def get_deck(
    deck_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> FlashcardDeckResponse:
    try:
        deck = await service.get_deck(db, current_user=current_user, deck_id=deck_id)
    except service.DeckNotFoundError:
        raise _deck_not_found_error() from None
    return FlashcardDeckResponse.model_validate(deck)


@decks_router.get("/{deck_id}/cards", response_model=list[FlashcardResponse])
@router.get("/decks/{deck_id}/cards", response_model=list[FlashcardResponse])
async def list_cards(
    deck_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[FlashcardResponse]:
    try:
        cards = await service.list_cards(
            db,
            current_user=current_user,
            deck_id=deck_id,
        )
    except service.DeckNotFoundError:
        raise _deck_not_found_error() from None
    return [FlashcardResponse.model_validate(card) for card in cards]


@router.post(
    "/{flashcard_id}/reviews",
    response_model=FlashcardReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def review_flashcard(
    flashcard_id: UUID,
    payload: FlashcardReviewRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> FlashcardReviewResponse:
    _ = payload
    try:
        progress = await service.review_flashcard(
            db,
            current_user=current_user,
            flashcard_id=flashcard_id,
        )
        await db.commit()
        await db.refresh(progress)
    except service.FlashcardNotFoundError:
        await db.rollback()
        raise _flashcard_not_found_error() from None
    return FlashcardReviewResponse.model_validate(progress)


@quizzes_router.post(
    "/generate",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/quizzes/generate",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_quiz(
    payload: QuizGenerateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> QuizResponse:
    try:
        quiz = await service.generate_quiz(
            db,
            current_user=current_user,
            document_ids=payload.document_ids,
            title=payload.title,
            question_count=payload.question_count,
            question_types=payload.question_types,
        )
        await db.commit()
        await db.refresh(quiz)
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    except service.GenerationDependencyError:
        await db.rollback()
        raise _generation_failed_error() from None
    except service.GeneratedPayloadInvalidError as exc:
        await db.rollback()
        raise _generated_payload_invalid_error(str(exc)) from None
    return QuizResponse.model_validate(quiz)


@quizzes_router.get("", response_model=list[QuizResponse])
@router.get("/quizzes", response_model=list[QuizResponse])
async def list_quizzes(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[QuizResponse]:
    quizzes = await service.list_quizzes(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return [QuizResponse.model_validate(quiz) for quiz in quizzes]


@quizzes_router.get("/{quiz_id}", response_model=QuizResponse)
@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> QuizResponse:
    try:
        quiz = await service.get_quiz(db, current_user=current_user, quiz_id=quiz_id)
    except service.QuizNotFoundError:
        raise _quiz_not_found_error() from None
    return QuizResponse.model_validate(quiz)


@quizzes_router.get("/{quiz_id}/questions", response_model=list[QuizQuestionResponse])
@router.get("/quizzes/{quiz_id}/questions", response_model=list[QuizQuestionResponse])
async def list_quiz_questions(
    quiz_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[QuizQuestionResponse]:
    try:
        questions = await service.list_quiz_questions(
            db,
            current_user=current_user,
            quiz_id=quiz_id,
        )
    except service.QuizNotFoundError:
        raise _quiz_not_found_error() from None
    return [QuizQuestionResponse.model_validate(question) for question in questions]


@quizzes_router.post(
    "/{quiz_id}/answers",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/quizzes/{quiz_id}/answers",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_quiz_answers(
    quiz_id: UUID,
    payload: QuizAnswerSubmitRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> QuizAttemptResponse:
    try:
        attempt = await service.submit_quiz_answers(
            db,
            current_user=current_user,
            quiz_id=quiz_id,
            answers=payload.answers,
        )
        await db.commit()
        await db.refresh(attempt)
    except service.QuizNotFoundError:
        await db.rollback()
        raise _quiz_not_found_error() from None
    return QuizAttemptResponse.model_validate(attempt)


@quizzes_router.get("/{quiz_id}/results", response_model=list[QuizAttemptResponse])
@router.get("/quizzes/{quiz_id}/results", response_model=list[QuizAttemptResponse])
async def get_quiz_results(
    quiz_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[QuizAttemptResponse]:
    try:
        attempts = await service.get_quiz_results(
            db,
            current_user=current_user,
            quiz_id=quiz_id,
        )
    except service.QuizNotFoundError:
        raise _quiz_not_found_error() from None
    return [QuizAttemptResponse.model_validate(attempt) for attempt in attempts]


def _document_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="document_not_found",
        message="Document not found",
    )


def _document_not_ready_error() -> AppError:
    return AppError(
        status_code=status.HTTP_409_CONFLICT,
        error_code="document_not_ready",
        message="Document is not ready for generation",
    )


def _generation_failed_error() -> AppError:
    return AppError(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        error_code="generation_failed",
        message="Generation dependency is unavailable",
    )


def _generated_payload_invalid_error(message: str) -> AppError:
    return AppError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="generated_payload_invalid",
        message=message or "Generated payload is invalid",
    )


def _deck_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="deck_not_found",
        message="Flashcard deck not found",
    )


def _flashcard_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="flashcard_not_found",
        message="Flashcard not found",
    )


def _quiz_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="quiz_not_found",
        message="Quiz not found",
    )
