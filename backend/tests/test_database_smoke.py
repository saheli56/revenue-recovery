import pytest
import uuid
from datetime import datetime, timezone
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

@pytest.mark.asyncio
async def test_database_models_roundtrip():
    test_run_id = uuid.uuid4().hex[:8]
    source_ref = f"sub_test_pytest_{test_run_id}"

    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.subscription_failure,
            source_reference=source_ref,
            customer_id=f"cust_pytest_{test_run_id}",
            amount=4999.0,
            currency="INR",
            status="open"
        )
        session.add(case)
        await session.flush()
        case_id = case.id

        diagnosis = Diagnosis(
            case_id=case_id,
            root_cause="card_expired",
            confidence=1.0,
            evidence={"error_code": "card_expired", "retry_count": 0},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()
        diagnosis_id = diagnosis.id

        decision = Decision(
            case_id=case_id,
            diagnosis_id=diagnosis_id,
            chosen_action="send_update_payment_method_link",
            justification="Card expired requires customer to update method without automatic retries",
            policy_rule_id="RULE_CARD_EXPIRED_01",
            guardrail_checks_passed=True
        )
        session.add(decision)
        await session.flush()
        decision_id = decision.id

        execution = Execution(
            decision_id=decision_id,
            channel="simulated_email_service",
            external_reference=f"msg_sent_{test_run_id}",
            status="delivered",
            raw_response={"channel": "email", "status": "delivered", "timestamp": "2026-08-28T10:00:00Z"}
        )
        session.add(execution)
        await session.flush()

        outcome = Outcome(
            case_id=case_id,
            recovered=True,
            recovered_amount=4999.0,
            recovered_at=datetime.now(timezone.utc),
            final_status=FinalStatus.recovered
        )
        session.add(outcome)
        await session.flush()
        outcome_id = outcome.id

        audit = AuditLog(
            case_id=case_id,
            stage="strategist",
            event="decision_created",
            payload={"rule": "RULE_CARD_EXPIRED_01", "guardrail_passed": True, "run_id": test_run_id}
        )
        session.add(audit)
        await session.commit()

    async with async_session_factory() as session:
        queried_case = await session.get(RecoveryCase, case_id)
        assert queried_case is not None
        assert queried_case.source_reference == source_ref
        assert queried_case.amount == 4999.0
        assert queried_case.case_type == CaseType.subscription_failure

        queried_diagnosis = await session.get(Diagnosis, diagnosis_id)
        assert queried_diagnosis is not None
        assert queried_diagnosis.root_cause == "card_expired"
        assert queried_diagnosis.confidence == 1.0

        queried_decision = await session.get(Decision, decision_id)
        assert queried_decision is not None
        assert queried_decision.guardrail_checks_passed is True

        exec_res = await session.execute(select(Execution).where(Execution.decision_id == decision_id))
        queried_exec = exec_res.scalars().first()
        assert queried_exec is not None
        assert queried_exec.channel == "simulated_email_service"

        queried_out = await session.get(Outcome, outcome_id)
        assert queried_out is not None
        assert queried_out.recovered is True
        assert queried_out.final_status == FinalStatus.recovered

        audit_res = await session.execute(select(AuditLog).where(AuditLog.case_id == case_id))
        queried_audit = audit_res.scalars().first()
        assert queried_audit is not None
        assert queried_audit.stage == "strategist"
