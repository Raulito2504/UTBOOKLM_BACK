from fastapi import APIRouter

from src.modules.admin.router import router as admin_router
from src.modules.auth.router import router as auth_router
from src.modules.dashboard.router import router as dashboard_router
from src.modules.documents.router import router as documents_router
from src.modules.flashcards.router import decks_router, quizzes_router
from src.modules.flashcards.router import router as flashcards_router
from src.modules.notebooks.router import router as notebooks_router
from src.modules.notifications.router import router as notifications_router
from src.modules.organizations.router import router as organizations_router
from src.modules.rag_chat.router import router as rag_chat_router
from src.modules.rooms.router import router as rooms_router
from src.modules.streaks.router import router as streaks_router
from src.modules.users.router import router as users_router
from src.modules.webtour.router import router as webtour_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(organizations_router, prefix="/orgs", tags=["organizations"])
api_router.include_router(documents_router, prefix="/docs", tags=["documents"])
api_router.include_router(flashcards_router, prefix="/flashcards", tags=["flashcards"])
api_router.include_router(decks_router, prefix="/flashcard-decks", tags=["flashcards"])
api_router.include_router(quizzes_router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(notebooks_router, prefix="/notebooks", tags=["notebooks"])
api_router.include_router(rag_chat_router, prefix="/rag", tags=["rag"])
api_router.include_router(rooms_router, prefix="/rooms", tags=["rooms"])
api_router.include_router(streaks_router, prefix="/streaks", tags=["streaks"])
api_router.include_router(webtour_router, prefix="/webtour", tags=["webtour"])
