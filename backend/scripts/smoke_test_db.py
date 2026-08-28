import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from database import async_session_factory
from models import (
    RecoveryCase,
    Diagnosis,
    Decision,
    Execution,
    Outcome,
    AuditLog,
    CaseType,
    DiagnosisMethod,
    FinalStatus
)

async def run_db_smoke_test():
    test_run_id = uuid.uuid4().hex[:8]
    source_ref = f"test_ref_{test_run_id}"

    async with async_session_factory() as session:
        test_case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=source_ref,
            customer_id=f"cust_test_{test_run_id}",
            amount=2499.0,
            currency="INR",
            status="open"
        )
        session.add(test_case)
        await session.flush()
        case_id = test_case.id

        test_diagnosis = Diagnosis(
            case_id=case_id,
            root_cause="insufficient_funds",
            confidence=0.98,
            evidence={"error_code": "insufficient_funds", "declined_at_gateway": True},
            method=DiagnosisMethod.rule
        )
        session.add(test_diagnosis)
        await session.flush()
        diagnosis_id = test_diagnosis.id

        test_decision = Decision(
            case_id=case_id,
            diagnosis_id=diagnosis_id,
            chosen_action="delayed_retry_day_3",
            justification="Policy specifies retry on payday window with max 3 attempts",
            policy_rule_id="RULE_INSUFFICIENT_FUNDS_01",
            guardrail_checks_passed=True
        )
        session.add(test_decision)
        await session.flush()
        decision_id = test_decision.id

        test_execution = Execution(
            decision_id=decision_id,
            channel="razorpay_payment_links_api",
            external_reference=f"plink_{test_run_id}",
            status="success",
            raw_response={"id": f"plink_{test_run_id}", "status": "created", "short_url": "https://rzp.io/i/test"}
        )
        session.add(test_execution)
        await session.flush()

        test_outcome = Outcome(
            case_id=case_id,
            recovered=True,
            recovered_amount=2499.0,
            recovered_at=datetime.now(timezone.utc),
            final_status=FinalStatus.recovered
        )
        session.add(test_outcome)
        await session.flush()

        test_audit = AuditLog(
            case_id=case_id,
            stage="smoke_test",
            event="test_cycle_completed",
            payload={"verified_tables": 6, "status": "ok", "run_id": test_run_id}
        )
        session.add(test_audit)
        await session.commit()

    async with async_session_factory() as session:
        case_result = await session.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
        fetched_case = case_result.scalar_one_or_none()
        assert fetched_case is not None
        assert fetched_case.source_reference == source_ref
        assert fetched_case.amount == 2499.0

        diag_result = await session.execute(select(Diagnosis).where(Diagnosis.case_id == case_id))
        fetched_diag = diag_result.scalar_one_or_none()
        assert fetched_diag is not None
        assert fetched_diag.root_cause == "insufficient_funds"

        dec_result = await session.execute(select(Decision).where(Decision.case_id == case_id))
        fetched_dec = dec_result.scalar_one_or_none()
        assert fetched_dec is not None
        assert fetched_dec.policy_rule_id == "RULE_INSUFFICIENT_FUNDS_01"

        exec_result = await session.execute(select(Execution).where(Execution.decision_id == decision_id))
        fetched_exec = exec_result.scalar_one_or_none()
        assert fetched_exec is not None
        assert fetched_exec.external_reference == f"plink_{test_run_id}"

        out_result = await session.execute(select(Outcome).where(Outcome.case_id == case_id))
        fetched_out = out_result.scalar_one_or_none()
        assert fetched_out is not None
        assert fetched_out.recovered is True
        assert fetched_out.final_status == FinalStatus.recovered

        audit_result = await session.execute(select(AuditLog).where(AuditLog.case_id == case_id))
        fetched_audit = audit_result.scalar_one_or_none()
        assert fetched_audit is not None
        assert fetched_audit.event == "test_cycle_completed"

    print("Phase 1 DB Smoke Test: SUCCESS. All 6 models verified with full round-trip persistence.")

if __name__ == "__main__":
    asyncio.run(run_db_smoke_test())
