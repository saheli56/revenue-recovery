import sys
import os
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import RecoveryCase, Diagnosis, Decision, Execution, Outcome, AuditLog
from schemas import CaseTraceResponse, RecoveryCaseResponse, DiagnosisResponse, DecisionResponse, ExecutionResponse, OutcomeResponse, AuditLogResponse

class AuditorService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_full_case_trace(self, case_id: int) -> Optional[CaseTraceResponse]:
        case = await self.session.get(RecoveryCase, case_id)
        if not case:
            return None

        diag_stmt = select(Diagnosis).where(Diagnosis.case_id == case_id).order_by(Diagnosis.id.asc())
        diag_res = await self.session.execute(diag_stmt)
        diagnoses = diag_res.scalars().all()

        dec_stmt = select(Decision).where(Decision.case_id == case_id).order_by(Decision.id.asc())
        dec_res = await self.session.execute(dec_stmt)
        decisions = dec_res.scalars().all()

        decision_ids = [d.id for d in decisions]
        executions = []
        if decision_ids:
            exec_stmt = select(Execution).where(Execution.decision_id.in_(decision_ids)).order_by(Execution.id.asc())
            exec_res = await self.session.execute(exec_stmt)
            executions = exec_res.scalars().all()

        out_stmt = select(Outcome).where(Outcome.case_id == case_id).order_by(Outcome.id.asc())
        out_res = await self.session.execute(out_stmt)
        outcomes = out_res.scalars().all()

        audit_stmt = select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.id.asc())
        audit_res = await self.session.execute(audit_stmt)
        audit_logs = audit_res.scalars().all()

        return CaseTraceResponse(
            case=RecoveryCaseResponse.model_validate(case),
            diagnoses=[DiagnosisResponse.model_validate(d) for d in diagnoses],
            decisions=[DecisionResponse.model_validate(d) for d in decisions],
            executions=[ExecutionResponse.model_validate(e) for e in executions],
            outcomes=[OutcomeResponse.model_validate(o) for o in outcomes],
            audit_logs=[AuditLogResponse.model_validate(a) for a in audit_logs]
        )

    async def verify_unbroken_audit_trail(self, case_id: int) -> Dict[str, Any]:
        trace = await self.get_full_case_trace(case_id)
        if not trace:
            return {"valid": False, "reason": "Case not found"}

        stages_present = [log.stage for log in trace.audit_logs]

        has_ingestion = "ingestion" in stages_present
        has_detector = "detector" in stages_present
        has_outcome = "tracker" in stages_present

        if not (has_ingestion and has_detector and has_outcome):
            return {
                "valid": False,
                "case_id": case_id,
                "missing_essential_stages": True,
                "stages_present": stages_present
            }

        is_detector_excluded = any(
            log.stage == "detector" and log.event == "case_excluded_from_recovery"
            for log in trace.audit_logs
        )

        if not is_detector_excluded:
            has_diagnoser = "diagnoser" in stages_present
            has_strategist = "strategist" in stages_present
            has_executor = "executor" in stages_present
            if not (has_diagnoser and has_strategist and has_executor):
                return {
                    "valid": False,
                    "case_id": case_id,
                    "missing_active_stages": True,
                    "stages_present": stages_present
                }

        return {
            "valid": True,
            "case_id": case_id,
            "total_audit_events": len(trace.audit_logs),
            "stages_sequence": stages_present,
            "final_status": trace.outcomes[0].final_status.value if trace.outcomes else trace.case.status
        }
