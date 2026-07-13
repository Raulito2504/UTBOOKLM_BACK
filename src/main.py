from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import configure_logging


configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API REST para el sistema SaaS",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Probando"}
