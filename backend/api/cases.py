import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from models import RecoveryCase, AuditLog, CaseType
from schemas import RecoveryCaseResponse, CaseTraceResponse
from pipeline.auditor import AuditorService
from datagen.loader import load_synthetic_batch_into_db
from orchestrator.pipeline_runner import BatchOrchestrator
from api.auth import verify_api_key

router = APIRouter(prefix="/cases", tags=["Cases"])

async def get_db():
    async with async_session_factory() as session:
        yield session

class IngestCaseRequest(BaseModel):
    case_type: CaseType
    source_reference: str
    customer_id: str
    amount: float
    currency: str = "INR"
    auto_process: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BatchRunRequest(BaseModel):
    concurrency: int = 5
    limit: Optional[int] = None
    seed_fresh: bool = False

class PaginatedCasesResponse(BaseModel):
    items: List[RecoveryCaseResponse]
    total: int
    limit: int
    offset: int

@router.post("/ingest", response_model=RecoveryCaseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def ingest_case(
    req: IngestCaseRequest,
    db: AsyncSession = Depends(get_db)
):
    existing_stmt = select(RecoveryCase).where(RecoveryCase.source_reference == req.source_reference)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case with source_reference '{req.source_reference}' already exists"
        )

    now = datetime.now(timezone.utc)
    case = RecoveryCase(
        case_type=req.case_type,
        source_reference=req.source_reference,
        customer_id=req.customer_id,
        amount=req.amount,
        currency=req.currency,
        status="open",
        created_at=now
    )
    db.add(case)
    await db.flush()

    audit = AuditLog(
        case_id=case.id,
        stage="ingestion",
        event="raw_event_received",
        payload={
            "case_type": req.case_type.value,
            "source_reference": req.source_reference,
            "customer_id": req.customer_id,
            "amount": req.amount,
            "currency": req.currency,
            **req.metadata
        },
        timestamp=now
    )
    db.add(audit)
    await db.commit()
    await db.refresh(case)

    if req.auto_process:
        orchestrator = BatchOrchestrator(max_concurrency=1)
        await orchestrator.process_single_case_pipeline(case.id)
        async with async_session_factory() as refresh_session:
            case = await refresh_session.get(RecoveryCase, case.id)

    return case

@router.post("/batch-run", dependencies=[Depends(verify_api_key)])
async def trigger_batch_run(
    req: BatchRunRequest
):
    if req.seed_fresh:
        await load_synthetic_batch_into_db(clear_existing=True)

    orchestrator = BatchOrchestrator(max_concurrency=req.concurrency)
    summary = await orchestrator.run_batch(limit=req.limit)

    return {
        "status": "completed",
        "processed_count": summary.processed_count,
        "total_cases": summary.total_cases,
        "recovered_count": summary.recovered_count,
        "total_at_risk_amount": summary.total_at_risk_amount,
        "total_recovered_amount": summary.total_recovered_amount,
        "net_recovery_rate_pct": round((summary.total_recovered_amount / max(summary.total_at_risk_amount, 1.0)) * 100.0, 2),
        "elapsed_seconds": round(summary.elapsed_seconds, 2),
        "status_breakdown": summary.status_breakdown
    }

@router.get("", response_model=PaginatedCasesResponse, dependencies=[Depends(verify_api_key)])
async def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    case_type_filter: Optional[str] = Query(None, alias="case_type"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(RecoveryCase)

    conditions = []
    if status_filter:
        conditions.append(RecoveryCase.status == status_filter)
    if case_type_filter:
        conditions.append(RecoveryCase.case_type == case_type_filter)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                RecoveryCase.source_reference.ilike(search_pattern),
                RecoveryCase.customer_id.ilike(search_pattern)
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(RecoveryCase.id.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    return PaginatedCasesResponse(
        items=[RecoveryCaseResponse.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/{case_id}", response_model=RecoveryCaseResponse, dependencies=[Depends(verify_api_key)])
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    case = await db.get(RecoveryCase, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found")
    return case

@router.get("/{case_id}/trace", response_model=CaseTraceResponse, dependencies=[Depends(verify_api_key)])
async def get_case_audit_trace(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    auditor = AuditorService(db)
    trace = await auditor.get_full_case_trace(case_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found")
    return trace
