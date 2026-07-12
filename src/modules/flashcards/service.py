import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.models import (
    Document,
    DocumentStatus,
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamQuestionType,
    Flashcard,
    FlashcardDeck,
    FlashcardDifficulty,
    StudyProgress,
    User,
)
from src.modules.dashboard import service as dashboard_service
from src.modules.documents import repository as documents_repository
from src.modules.flashcards import repository
from src.modules.flashcards.schemas import (
    ExamQuestionDraft,
    FlashcardDraft,
    FlashcardPayload,
    QuizPayload,
)
from src.modules.rag_chat.llm_provider import (
    ProviderConfigurationError,
    ProviderRequestError,
    get_llm_provider,
)


class DocumentNotFoundError(Exception):
    pass


class DocumentNotReadyError(Exception):
    pass


class GenerationDependencyError(Exception):
    pass


class GeneratedPayloadInvalidError(Exception):
    pass


class DeckNotFoundError(Exception):
    pass


class FlashcardNotFoundError(Exception):
    pass


class QuizNotFoundError(Exception):
    pass


async def generate_flashcards(
    db: AsyncSession,
    *,
    current_user: User,
    document_ids: list[uuid.UUID],
    count: int,
    difficulty: FlashcardDifficulty,
    deck_name: str | None = None,
) -> FlashcardDeck:
    documents = await _validate_documents(
        db,
        current_user=current_user,
        document_ids=document_ids,
    )
    context = await _select_context(db, document_ids=document_ids)
    prompt = _build_flashcard_prompt(
        context=context,
        count=count,
        difficulty=difficulty,
    )
    payload = _generate_json_payload(prompt)
    try:
        generated = FlashcardPayload.model_validate(payload)
    except ValidationError as exc:
        raise GeneratedPayloadInvalidError(str(exc)) from exc

    cards = generated.flashcards[:count]
    cards = validate_flashcards(cards)
    deck = await repository.create_deck(
        db,
        user_id=current_user.id,
        document_id=documents[0].id if len(documents) == 1 else None,
        name=deck_name or _default_deck_name(documents),
    )
    for card in cards:
        await repository.create_flashcard(
            db,
            deck_id=deck.id,
            question=card.question,
            answer=card.answer,
            difficulty=card.difficulty,
        )
    await repository.update_deck_card_count(db, deck=deck, card_count=len(cards))
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="flashcard_deck_generated",
        metadata_json={
            "deck_id": str(deck.id),
            "document_ids": [str(document_id) for document_id in document_ids],
            "card_count": len(cards),
        },
    )
    return deck


async def list_decks(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[FlashcardDeck]:
    return await repository.list_decks_by_user(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


async def get_deck(
    db: AsyncSession,
    *,
    current_user: User,
    deck_id: uuid.UUID,
) -> FlashcardDeck:
    deck = await repository.get_deck_by_user(
        db,
        deck_id=deck_id,
        user_id=current_user.id,
    )
    if deck is None:
        raise DeckNotFoundError
    return deck


async def list_cards(
    db: AsyncSession,
    *,
    current_user: User,
    deck_id: uuid.UUID,
) -> list[Flashcard]:
    deck = await get_deck(db, current_user=current_user, deck_id=deck_id)
    return await repository.list_flashcards_by_deck(db, deck_id=deck.id)


async def review_flashcard(
    db: AsyncSession,
    *,
    current_user: User,
    flashcard_id: uuid.UUID,
) -> StudyProgress:
    flashcard = await repository.get_flashcard_by_user(
        db,
        flashcard_id=flashcard_id,
        user_id=current_user.id,
    )
    if flashcard is None:
        raise FlashcardNotFoundError
    progress = await repository.create_study_progress(
        db,
        user_id=current_user.id,
        flashcard_id=flashcard.id,
    )
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="flashcard_review",
        metadata_json={
            "flashcard_id": str(flashcard.id),
            "deck_id": str(flashcard.deck_id),
        },
    )
    return progress


async def generate_quiz(
    db: AsyncSession,
    *,
    current_user: User,
    document_ids: list[uuid.UUID],
    title: str | None,
    question_count: int,
    question_types: list[ExamQuestionType],
) -> Exam:
    documents = await _validate_documents(
        db,
        current_user=current_user,
        document_ids=document_ids,
    )
    context = await _select_context(db, document_ids=document_ids)
    prompt = _build_quiz_prompt(
        context=context,
        question_count=question_count,
        question_types=[str(item.value) for item in question_types],
    )
    payload = _generate_json_payload(prompt)
    try:
        generated = QuizPayload.model_validate(payload)
    except ValidationError as exc:
        raise GeneratedPayloadInvalidError(str(exc)) from exc

    questions = validate_exam_questions(generated.questions[:question_count])
    exam = await repository.create_exam(
        db,
        user_id=current_user.id,
        document_id=documents[0].id if len(documents) == 1 else None,
        title=title or _default_quiz_title(documents),
    )
    for question in questions:
        await repository.create_exam_question(
            db,
            exam_id=exam.id,
            question_type=question.question_type,
            prompt=question.prompt,
            options=question.options,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
        )
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="quiz_generated",
        metadata_json={
            "quiz_id": str(exam.id),
            "document_ids": [str(document_id) for document_id in document_ids],
            "question_count": len(questions),
        },
    )
    return exam


async def list_quizzes(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[Exam]:
    return await repository.list_exams_by_user(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


async def get_quiz(
    db: AsyncSession,
    *,
    current_user: User,
    quiz_id: uuid.UUID,
) -> Exam:
    exam = await repository.get_exam_by_user(
        db,
        exam_id=quiz_id,
        user_id=current_user.id,
    )
    if exam is None:
        raise QuizNotFoundError
    return exam


async def list_quiz_questions(
    db: AsyncSession,
    *,
    current_user: User,
    quiz_id: uuid.UUID,
) -> list[ExamQuestion]:
    quiz = await get_quiz(db, current_user=current_user, quiz_id=quiz_id)
    return await repository.list_exam_questions(db, exam_id=quiz.id)


async def submit_quiz_answers(
    db: AsyncSession,
    *,
    current_user: User,
    quiz_id: uuid.UUID,
    answers: dict[uuid.UUID, str],
) -> ExamAttempt:
    quiz = await get_quiz(db, current_user=current_user, quiz_id=quiz_id)
    questions = await repository.list_exam_questions(db, exam_id=quiz.id)
    score, feedback = _score_answers(questions=questions, answers=answers)
    attempt = await repository.create_exam_attempt(
        db,
        exam_id=quiz.id,
        user_id=current_user.id,
        answers={str(key): value for key, value in answers.items()},
        score=score,
        feedback=feedback,
    )
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="quiz_attempt_submitted",
        metadata_json={
            "quiz_id": str(quiz.id),
            "attempt_id": str(attempt.id),
            "score": score,
        },
    )
    return attempt


async def get_quiz_results(
    db: AsyncSession,
    *,
    current_user: User,
    quiz_id: uuid.UUID,
) -> list[ExamAttempt]:
    quiz = await get_quiz(db, current_user=current_user, quiz_id=quiz_id)
    return await repository.list_exam_attempts_by_user(
        db,
        exam_id=quiz.id,
        user_id=current_user.id,
    )


def validate_flashcards(items: list[FlashcardDraft]) -> list[FlashcardDraft]:
    if not items:
        raise GeneratedPayloadInvalidError("No flashcards were generated")
    return items


def validate_exam_questions(items: list[ExamQuestionDraft]) -> list[ExamQuestionDraft]:
    if not items:
        raise GeneratedPayloadInvalidError("No quiz questions were generated")
    return items


async def _validate_documents(
    db: AsyncSession,
    *,
    current_user: User,
    document_ids: list[uuid.UUID],
) -> list[Document]:
    documents: list[Document] = []
    for document_id in dict.fromkeys(document_ids):
        document = await documents_repository.get_document_by_organization(
            db,
            document_id=document_id,
            organization_id=current_user.organization_id,
        )
        if document is None:
            raise DocumentNotFoundError
        if document.status != DocumentStatus.READY:
            raise DocumentNotReadyError
        documents.append(document)
    return documents


async def _select_context(
    db: AsyncSession,
    *,
    document_ids: list[uuid.UUID],
) -> str:
    settings = get_settings()
    parts: list[str] = []
    current_length = 0
    for document_id in dict.fromkeys(document_ids):
        chunks = await documents_repository.list_document_chunks(
            db,
            document_id=document_id,
        )
        for chunk in chunks:
            text = (
                f"[document_id={chunk.document_id} chunk_id={chunk.id} "
                f"page={chunk.page_number}]\n{chunk.content}"
            )
            if current_length + len(text) > settings.rag_max_context_chars:
                if not parts:
                    return text[: settings.rag_max_context_chars]
                return "\n\n---\n\n".join(parts)
            parts.append(text)
            current_length += len(text)
    if not parts:
        raise GeneratedPayloadInvalidError("No document context is available")
    return "\n\n---\n\n".join(parts)


def _build_flashcard_prompt(
    *,
    context: str,
    count: int,
    difficulty: FlashcardDifficulty,
) -> str:
    return (
        "Eres un generador de material de estudio para UTBookLM.\n"
        "Usa solo el contexto proporcionado.\n"
        "Devuelve exclusivamente JSON valido, sin markdown.\n"
        "Genera flashcards claras y utiles para estudiar.\n"
        "No inventes datos que no aparezcan en el contexto.\n"
        f"Genera exactamente {count} flashcards de dificultad {difficulty.value}.\n\n"
        "Formato:\n"
        '{"flashcards":[{"question":"...","answer":"...",'
        '"difficulty":"easy|medium|hard"}]}\n\n'
        f"Contexto:\n{context}"
    )


def _build_quiz_prompt(
    *,
    context: str,
    question_count: int,
    question_types: list[str],
) -> str:
    return (
        "Eres un generador de mini examenes para UTBookLM.\n"
        "Usa solo el contexto proporcionado.\n"
        "Devuelve exclusivamente JSON valido, sin markdown.\n"
        "No inventes datos que no aparezcan en el contexto.\n"
        f"Genera exactamente {question_count} preguntas.\n"
        f"Tipos permitidos: {', '.join(question_types)}.\n\n"
        "Formato:\n"
        '{"questions":[{"question_type":"multiple_choice","prompt":"...",'
        '"options":{"A":"...","B":"...","C":"...","D":"..."},'
        '"correct_answer":"A","explanation":"..."}]}\n\n'
        f"Contexto:\n{context}"
    )


def _generate_json_payload(prompt: str) -> dict[str, Any]:
    try:
        response = get_llm_provider().complete(prompt)
    except (ProviderConfigurationError, ProviderRequestError) as exc:
        raise GenerationDependencyError(str(exc)) from exc

    try:
        return json.loads(_extract_json(response.content))
    except (TypeError, json.JSONDecodeError) as exc:
        raise GeneratedPayloadInvalidError(
            "Generated response is not valid JSON",
        ) from exc


def _extract_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _score_answers(
    *,
    questions: list[ExamQuestion],
    answers: dict[uuid.UUID, str],
) -> tuple[float, dict[str, Any]]:
    scorable = [question for question in questions if question.correct_answer]
    if not scorable:
        return 0.0, {"items": []}

    correct = 0
    items: list[dict[str, Any]] = []
    for question in questions:
        submitted = answers.get(question.id)
        expected = question.correct_answer
        is_correct = (
            expected is not None
            and submitted is not None
            and submitted.strip().lower() == expected.strip().lower()
        )
        if expected is not None and is_correct:
            correct += 1
        items.append(
            {
                "question_id": str(question.id),
                "submitted_answer": submitted,
                "correct_answer": expected,
                "is_correct": is_correct if expected is not None else None,
                "explanation": question.explanation,
            },
        )
    score = round((correct / len(scorable)) * 100, 2)
    return score, {"items": items}


def _default_deck_name(documents: list[Document]) -> str:
    if len(documents) == 1:
        return f"Flashcards: {documents[0].title}"[:255]
    return "Flashcards generadas"[:255]


def _default_quiz_title(documents: list[Document]) -> str:
    if len(documents) == 1:
        return f"Mini examen: {documents[0].title}"[:255]
    return "Mini examen generado"[:255]
