import pytest
import uuid
from sqlalchemy import select, and_
from database import async_session_factory
from models import RecoveryCase, Diagnosis, Decision, Execution, AuditLog, CaseType, DiagnosisMethod
from pipeline.executor import ExecutorService

@pytest.mark.asyncio
async def test_executor_razorpay_order_dispatch():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_exec_order_{test_run_id}",
            customer_id=f"cust_exec_{test_run_id}",
            amount=2999.0,
            currency="INR",
            status="decided"
        )
        session.add(case)
        await session.flush()

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause="issuer_timeout",
            confidence=1.0,
            evidence={"source": "test"},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()

        decision = Decision(
            case_id=case.id,
            diagnosis_id=diagnosis.id,
            chosen_action="immediate_single_retry",
            justification="Policy allows immediate retry on timeout",
            policy_rule_id="POL_ISSUER_TIMEOUT",
            guardrail_checks_passed=True
        )
        session.add(decision)
        await session.flush()

        executor = ExecutorService(session)
        execution = await executor.execute_single_decision(decision.id)

        assert execution is not None
        assert execution.channel == "razorpay_orders_api"
        assert execution.status == "dispatched"
        assert execution.external_reference is not None
        assert execution.external_reference.startswith("order_")
        assert execution.raw_response is not None

        audit_stmt = select(AuditLog).where(
            and_(AuditLog.case_id == case.id, AuditLog.stage == "executor")
        )
        audit_res = await session.execute(audit_stmt)
        exec_audit = audit_res.scalar_one_or_none()
        assert exec_audit is not None
        assert exec_audit.event == "action_executed"
        assert exec_audit.payload["channel"] == "razorpay_orders_api"

        await session.commit()

@pytest.mark.asyncio
async def test_executor_refuses_when_guardrail_failed():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_exec_refused_{test_run_id}",
            customer_id=f"cust_exec_refused_{test_run_id}",
            amount=1500.0,
            currency="INR",
            status="stopped_by_policy"
        )
        session.add(case)
        await session.flush()

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause="insufficient_funds",
            confidence=1.0,
            evidence={"source": "test"},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()

        decision = Decision(
            case_id=case.id,
            diagnosis_id=diagnosis.id,
            chosen_action="escalate_or_stop_by_policy",
            justification="Guardrail blocked action: MAX_RETRIES_EXCEEDED",
            policy_rule_id="POL_INSUFFICIENT_FUNDS",
            guardrail_checks_passed=False
        )
        session.add(decision)
        await session.flush()

        executor = ExecutorService(session)
        execution = await executor.execute_single_decision(decision.id)

        assert execution is not None
        assert execution.status == "refused_by_guardrails"
        assert execution.channel == "guardrail_circuit_breaker"
        assert execution.external_reference is None

        audit_stmt = select(AuditLog).where(
            and_(AuditLog.case_id == case.id, AuditLog.stage == "executor")
        )
        audit_res = await session.execute(audit_stmt)
        exec_audit = audit_res.scalar_one_or_none()
        assert exec_audit is not None
        assert exec_audit.event == "execution_refused_guardrail_failed"

        await session.commit()
