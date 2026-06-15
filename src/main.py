from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API REST para el sistema SaaS",
    version=settings.app_version,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Probando"}
