from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.modules.dashboard import service
from src.modules.dashboard.schemas import (
    DashboardActivityResponse,
    DashboardMetricsResponse,
    NotebookCardResponse,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "dashboard", "status": "ready"}


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_metrics(
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DashboardMetricsResponse:
    return await service.get_metrics(db, current_user=current_user)


@router.get("/activity", response_model=list[DashboardActivityResponse])
async def list_activity(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[DashboardActivityResponse]:
    activities = await service.list_activities(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return [
        DashboardActivityResponse.model_validate(activity)
        for activity in activities
    ]


@router.get("/notebooks", response_model=list[NotebookCardResponse])
async def list_notebooks(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[NotebookCardResponse]:
    return await service.list_notebooks(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
