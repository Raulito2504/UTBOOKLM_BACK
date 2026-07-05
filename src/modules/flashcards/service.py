from src.modules.flashcards.schemas import ExamQuestionDraft, FlashcardDraft


def validate_flashcards(items: list[FlashcardDraft]) -> list[FlashcardDraft]:
    return items


def validate_exam_questions(items: list[ExamQuestionDraft]) -> list[ExamQuestionDraft]:
    return items
