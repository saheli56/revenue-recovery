import asyncio
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from models import RecoveryCase, AuditLog, FinalStatus
from pipeline.detector import DetectorService
from pipeline.diagnoser import DiagnoserService
from pipeline.strategist import StrategistService
from pipeline.executor import ExecutorService
from pipeline.tracker import OutcomeTrackerService

@dataclass
class CaseExecutionResult:
    case_id: int
    source_reference: str
    amount: float
    final_status: str
    is_recovered: bool
    stages_completed: List[str] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class BatchExecutionSummary:
    total_cases: int = 0
    processed_count: int = 0
    recovered_count: int = 0
    total_at_risk_amount: float = 0.0
    total_recovered_amount: float = 0.0
    status_breakdown: Dict[str, int] = field(default_factory=dict)
    case_results: List[CaseExecutionResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0

_db_lock = asyncio.Lock()

class BatchOrchestrator:
    def __init__(self, max_concurrency: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def process_single_case_pipeline(self, case_id: int) -> CaseExecutionResult:
        async with self.semaphore:
            async with _db_lock:
                stages_completed: List[str] = []
                async with async_session_factory() as session:
                    case = await session.get(RecoveryCase, case_id)
                    if not case:
                        return CaseExecutionResult(
                            case_id=case_id,
                            source_reference="unknown",
                            amount=0.0,
                            final_status="not_found",
                            is_recovered=False,
                            error="Case not found in database"
                        )

                    source_ref = case.source_reference
                    amount = case.amount

                    try:
                        detector = DetectorService(session)
                        det_res = await detector.detect_single_case(case_id)
                        stages_completed.append("detector")

                        if not det_res or det_res.is_excluded:
                            tracker = OutcomeTrackerService(session)
                            out_res = await tracker.resolve_case_outcome(case_id)
                            await session.commit()
                            stages_completed.append("tracker")
                            return CaseExecutionResult(
                                case_id=case_id,
                                source_reference=source_ref,
                                amount=amount,
                                final_status=FinalStatus.stopped_by_policy.value,
                                is_recovered=False,
                                stages_completed=stages_completed
                            )

                        diagnoser = DiagnoserService(session)
                        diag = await diagnoser.diagnose_single_case(case_id)
                        stages_completed.append("diagnoser")

                        strategist = StrategistService(session)
                        decision = await strategist.decide_single_case(case_id)
                        stages_completed.append("strategist")

                        executor = ExecutorService(session)
                        execution = await executor.execute_single_decision(decision.id)
                        stages_completed.append("executor")

                        tracker = OutcomeTrackerService(session)
                        outcome = await tracker.resolve_case_outcome(case_id)
                        stages_completed.append("tracker")

                        await session.commit()

                        return CaseExecutionResult(
                            case_id=case_id,
                            source_reference=source_ref,
                            amount=amount,
                            final_status=outcome.final_status.value if outcome else "completed",
                            is_recovered=outcome.recovered if outcome else False,
                            stages_completed=stages_completed
                        )

                    except Exception as exc:
                        await session.rollback()
                        async with async_session_factory() as err_session:
                            err_case = await err_session.get(RecoveryCase, case_id)
                            if err_case:
                                err_case.status = "stage_failure"
                                err_audit = AuditLog(
                                    case_id=case_id,
                                    stage="orchestrator",
                                    event="stage_execution_failed",
                                    payload={
                                        "error": str(exc),
                                        "stages_completed": stages_completed,
                                        "timestamp": datetime.now(timezone.utc).isoformat()
                                    },
                                    timestamp=datetime.now(timezone.utc)
                                )
                                err_session.add(err_audit)
                                await err_session.commit()

                        return CaseExecutionResult(
                            case_id=case_id,
                            source_reference=source_ref,
                            amount=amount,
                            final_status="stage_failure",
                            is_recovered=False,
                            stages_completed=stages_completed,
                            error=str(exc)
                        )

    async def run_batch(self, limit: Optional[int] = None) -> BatchExecutionSummary:
        start_time = datetime.now(timezone.utc)

        async with async_session_factory() as session:
            stmt = select(RecoveryCase.id, RecoveryCase.amount).order_by(RecoveryCase.id.asc())
            if limit:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            rows = result.all()
            case_ids = [r[0] for r in rows]
            total_at_risk = sum(r[1] for r in rows)

        total_cases = len(case_ids)
        tasks = [self.process_single_case_pipeline(cid) for cid in case_ids]
        results: List[CaseExecutionResult] = await asyncio.gather(*tasks)

        end_time = datetime.now(timezone.utc)
        elapsed = (end_time - start_time).total_seconds()

        status_counts: Dict[str, int] = {}
        recovered_count = 0
        total_recovered_val = 0.0

        for r in results:
            status_counts[r.final_status] = status_counts.get(r.final_status, 0) + 1
            if r.is_recovered:
                recovered_count += 1
                total_recovered_val += r.amount

        return BatchExecutionSummary(
            total_cases=total_cases,
            processed_count=len(results),
            recovered_count=recovered_count,
            total_at_risk_amount=total_at_risk,
            total_recovered_amount=total_recovered_val,
            status_breakdown=status_counts,
            case_results=results,
            elapsed_seconds=elapsed
        )
