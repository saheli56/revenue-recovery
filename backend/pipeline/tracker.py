import hashlib
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import RecoveryCase, Decision, Execution, Outcome, AuditLog, FinalStatus

class OutcomeTrackerService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    def _determine_recovery_success(self, case: RecoveryCase, execution: Execution) -> bool:
        seed_str = f"outcome:{case.source_reference}:{execution.id}:{case.amount}"
        hash_val = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        probability = (hash_val % 100) / 100.0

        if execution.channel in ["razorpay_orders_api", "razorpay_payment_links_api"]:
            return probability < 0.78
        if execution.channel == "simulated_whatsapp_service":
            return probability < 0.68
        if execution.channel == "simulated_email_service":
            return probability < 0.62
        if execution.channel == "simulated_sms_service":
            return probability < 0.58
        return False

    async def resolve_case_outcome(self, case_id: int) -> Optional[Outcome]:
        case = await self.session.get(RecoveryCase, case_id)
        if not case:
            return None

        existing_outcome_stmt = select(Outcome).where(Outcome.case_id == case_id)
        existing_res = await self.session.execute(existing_outcome_stmt)
        existing_outcome = existing_res.scalars().first()
        if existing_outcome:
            return existing_outcome

        if case.status == "excluded":
            outcome = Outcome(
                case_id=case.id,
                recovered=False,
                recovered_amount=0.0,
                recovered_at=None,
                final_status=FinalStatus.stopped_by_policy
            )
            self.session.add(outcome)
            await self.session.flush()

            audit = AuditLog(
                case_id=case.id,
                stage="tracker",
                event="outcome_resolved",
                payload={
                    "outcome_id": outcome.id,
                    "recovered": False,
                    "final_status": FinalStatus.stopped_by_policy.value,
                    "reason": "Case excluded at detector stage"
                },
                timestamp=datetime.now(timezone.utc)
            )
            self.session.add(audit)
            await self.session.flush()
            return outcome

        exec_stmt = (
            select(Execution)
            .join(Decision, Execution.decision_id == Decision.id)
            .where(Decision.case_id == case_id)
            .order_by(Execution.id.desc())
        )
        exec_res = await self.session.execute(exec_stmt)
        latest_execution = exec_res.scalars().first()

        if not latest_execution:
            return None

        now = datetime.now(timezone.utc)

        if latest_execution.status == "refused_by_guardrails":
            recovered = False
            recovered_amount = 0.0
            recovered_at = None
            final_status = FinalStatus.stopped_by_policy
            resolution_reason = "Execution halted by safety guardrails"

        elif latest_execution.channel == "simulated_internal_escalation":
            recovered = False
            recovered_amount = 0.0
            recovered_at = None
            final_status = FinalStatus.escalated
            resolution_reason = "Case escalated to manual operations review queue"

        elif latest_execution.status in ["dispatched", "delivered"]:
            is_success = self._determine_recovery_success(case, latest_execution)
            if is_success:
                recovered = True
                recovered_amount = case.amount
                recovered_at = now
                final_status = FinalStatus.recovered
                resolution_reason = "Payment successfully captured and confirmed"
            else:
                recovered = False
                recovered_amount = 0.0
                recovered_at = None
                final_status = FinalStatus.failed
                resolution_reason = "Customer did not complete payment within window"
        else:
            recovered = False
            recovered_amount = 0.0
            recovered_at = None
            final_status = FinalStatus.failed
            resolution_reason = f"Execution delivery failed ({latest_execution.status})"

        outcome = Outcome(
            case_id=case.id,
            recovered=recovered,
            recovered_amount=recovered_amount,
            recovered_at=recovered_at,
            final_status=final_status
        )
        self.session.add(outcome)
        await self.session.flush()

        case.status = final_status.value

        audit = AuditLog(
            case_id=case.id,
            stage="tracker",
            event="outcome_resolved",
            payload={
                "outcome_id": outcome.id,
                "recovered": recovered,
                "recovered_amount": recovered_amount,
                "final_status": final_status.value,
                "reason": resolution_reason,
                "execution_channel": latest_execution.channel,
                "external_reference": latest_execution.external_reference
            },
            timestamp=now
        )
        self.session.add(audit)
        await self.session.flush()

        return outcome

    async def run_tracker_batch(self, limit: Optional[int] = None) -> List[Outcome]:
        stmt = select(RecoveryCase).order_by(RecoveryCase.id.asc())
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        cases = result.scalars().all()

        outcomes: List[Outcome] = []
        for case in cases:
            outcome = await self.resolve_case_outcome(case.id)
            if outcome:
                outcomes.append(outcome)

        await self.session.commit()
        return outcomes
