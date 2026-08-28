import os
import sys
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from evaluation.harness import EvaluationHarness, EvaluationReport
from api.auth import verify_api_key

router = APIRouter(prefix="/analytics", tags=["Analytics"])

async def get_db():
    async with async_session_factory() as session:
        yield session

@router.get("/summary", dependencies=[Depends(verify_api_key)])
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    harness = EvaluationHarness(db)
    report: EvaluationReport = await harness.generate_report()

    return {
        "generated_at": report.generated_at,
        "total_cases": report.total_cases,
        "total_at_risk_amount": report.total_at_risk_amount,
        "total_recovered_amount": report.total_recovered_amount,
        "gross_recovery_rate_pct": report.gross_recovery_rate_pct,
        "total_intervention_cost": report.total_intervention_cost,
        "net_recovered_amount": report.net_recovered_amount,
        "roi_multiplier": report.roi_multiplier,
        "precision_metric": report.precision_metric.model_dump(),
        "time_to_recovery_distribution": report.time_to_recovery_distribution
    }

@router.get("/breakdown", response_model=EvaluationReport, dependencies=[Depends(verify_api_key)])
async def get_analytics_full_breakdown(
    db: AsyncSession = Depends(get_db)
):
    harness = EvaluationHarness(db)
    report: EvaluationReport = await harness.generate_report()
    return report
