import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from database import async_session_factory
from models import RecoveryCase, Diagnosis, Decision, Execution, Outcome, AuditLog, CaseType, DiagnosisMethod, FinalStatus
from pipeline.tracker import OutcomeTrackerService
from pipeline.auditor import AuditorService

@pytest.mark.asyncio
async def test_outcome_tracking_recovered_and_audit_trail():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_track_{test_run_id}",
            customer_id=f"cust_track_{test_run_id}",
            amount=3499.0,
            currency="INR",
            status="open"
        )
        session.add(case)
        await session.flush()

        ingest_audit = AuditLog(
            case_id=case.id,
            stage="ingestion",
            event="raw_event_received",
            payload={"error_code": "issuer_timeout"}
        )
        session.add(ingest_audit)

        det_audit = AuditLog(
            case_id=case.id,
            stage="detector",
            event="case_qualified_at_risk",
            payload={"decision": "qualified"}
        )
        session.add(det_audit)

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause="issuer_timeout",
            confidence=1.0,
            evidence={"source": "test"},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()

        diag_audit = AuditLog(
            case_id=case.id,
            stage="diagnoser",
            event="diagnosis_completed",
            payload={"root_cause": "issuer_timeout"}
        )
        session.add(diag_audit)

        decision = Decision(
            case_id=case.id,
            diagnosis_id=diagnosis.id,
            chosen_action="immediate_single_retry",
            justification="Single retry allowed",
            policy_rule_id="POL_ISSUER_TIMEOUT",
            guardrail_checks_passed=True
        )
        session.add(decision)
        await session.flush()

        strat_audit = AuditLog(
            case_id=case.id,
            stage="strategist",
            event="decision_created",
            payload={"chosen_action": "immediate_single_retry"}
        )
        session.add(strat_audit)

        execution = Execution(
            decision_id=decision.id,
            channel="razorpay_orders_api",
            external_reference=f"order_{test_run_id}",
            status="dispatched",
            raw_response={"status": "created"}
        )
        session.add(execution)
        await session.flush()

        exec_audit = AuditLog(
            case_id=case.id,
            stage="executor",
            event="action_executed",
            payload={"channel": "razorpay_orders_api"}
        )
        session.add(exec_audit)
        await session.commit()

        tracker = OutcomeTrackerService(session)
        outcome = await tracker.resolve_case_outcome(case.id)
        await session.commit()

        assert outcome is not None
        assert outcome.final_status in [FinalStatus.recovered, FinalStatus.failed]
        if outcome.recovered:
            assert outcome.recovered_amount == 3499.0
            assert outcome.recovered_at is not None

        auditor = AuditorService(session)
        verification = await auditor.verify_unbroken_audit_trail(case.id)
        assert verification["valid"] is True
        assert "ingestion" in verification["stages_sequence"]
        assert "detector" in verification["stages_sequence"]
        assert "diagnoser" in verification["stages_sequence"]
        assert "strategist" in verification["stages_sequence"]
        assert "executor" in verification["stages_sequence"]
        assert "tracker" in verification["stages_sequence"]

@pytest.mark.asyncio
async def test_outcome_tracking_guardrail_halt_and_exclusion():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        excluded_case = RecoveryCase(
            case_type=CaseType.checkout_abandonment,
            source_reference=f"txn_excl_track_{test_run_id}",
            customer_id=f"cust_excl_{test_run_id}",
            amount=1200.0,
            currency="INR",
            status="excluded"
        )
        session.add(excluded_case)
        await session.flush()

        ingest_audit = AuditLog(
            case_id=excluded_case.id,
            stage="ingestion",
            event="raw_event_received",
            payload={"is_fraud_flagged": True}
        )
        session.add(ingest_audit)

        det_audit = AuditLog(
            case_id=excluded_case.id,
            stage="detector",
            event="case_excluded_from_recovery",
            payload={"decision": "excluded", "reason": "FRAUD_DISQUALIFIED"}
        )
        session.add(det_audit)
        await session.commit()

        tracker = OutcomeTrackerService(session)
        outcome = await tracker.resolve_case_outcome(excluded_case.id)
        await session.commit()

        assert outcome is not None
        assert outcome.recovered is False
        assert outcome.final_status == FinalStatus.stopped_by_policy

        auditor = AuditorService(session)
        verification = await auditor.verify_unbroken_audit_trail(excluded_case.id)
        assert verification["valid"] is True
