from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummary,
    SpendingByCategory,
    SpendingByMonth,
    SpendingByStore,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    svc = DashboardService(db, user)
    return await svc.get_summary(date_from=date_from, date_to=date_to)


@router.get("/spending-by-store", response_model=list[SpendingByStore])
async def spending_by_store(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SpendingByStore]:
    svc = DashboardService(db, user)
    return await svc.spending_by_store(date_from=date_from, date_to=date_to)


@router.get("/spending-by-month", response_model=list[SpendingByMonth])
async def spending_by_month(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SpendingByMonth]:
    svc = DashboardService(db, user)
    return await svc.spending_by_month(date_from=date_from, date_to=date_to)


@router.get("/spending-by-category", response_model=list[SpendingByCategory])
async def spending_by_category(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SpendingByCategory]:
    svc = DashboardService(db, user)
    return await svc.spending_by_category(date_from=date_from, date_to=date_to)
