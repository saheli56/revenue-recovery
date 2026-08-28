import pytest
import uuid
from sqlalchemy import select, and_, delete
from database import async_session_factory
from models import RecoveryCase, Diagnosis, Decision, Execution, AuditLog, CaseType, DiagnosisMethod
from pipeline.strategist import StrategistService

@pytest.mark.asyncio
async def test_strategist_action_selection_per_root_cause():
    test_run_id = uuid.uuid4().hex[:6]
    test_matrix = [
        ("insufficient_funds", CaseType.payment_failure, "POL_INSUFFICIENT_FUNDS", "delayed_retry_smart_schedule"),
        ("card_expired", CaseType.payment_failure, "POL_CARD_EXPIRED", "send_update_payment_method_link"),
        ("issuer_timeout", CaseType.payment_failure, "POL_ISSUER_TIMEOUT", "immediate_single_retry"),
        ("authentication_failed", CaseType.payment_failure, "POL_AUTH_FAILED", "send_fresh_payment_link"),
        ("subscription_mandate_exhausted", CaseType.subscription_failure, "POL_SUB_EXHAUSTED", "escalate_to_human_recovery_queue")
    ]

    async with async_session_factory() as session:
        for idx, (cause, ctype, expected_rule, expected_action) in enumerate(test_matrix):
            case = RecoveryCase(
                case_type=ctype,
                source_reference=f"txn_strat_{test_run_id}_{idx}",
                customer_id=f"cust_strat_{test_run_id}_{idx}",
                amount=1500.0,
                currency="INR",
                status="diagnosed"
            )
            session.add(case)
            await session.flush()

            await session.execute(delete(Decision).where(Decision.case_id == case.id))
            await session.execute(delete(Diagnosis).where(Diagnosis.case_id == case.id))
            await session.flush()

            diagnosis = Diagnosis(
                case_id=case.id,
                root_cause=cause,
                confidence=1.0,
                evidence={"source": "unit_test"},
                method=DiagnosisMethod.rule
            )
            session.add(diagnosis)
            await session.flush()

            strategist = StrategistService(session, kill_switch_active=False)
            decision = await strategist.decide_single_case(case.id)

            assert decision is not None
            assert decision.policy_rule_id == expected_rule
            assert decision.chosen_action == expected_action, f"Justification: {decision.justification}"
            assert decision.guardrail_checks_passed is True
            assert len(decision.justification) > 10

            audit_stmt = select(AuditLog).where(
                and_(AuditLog.case_id == case.id, AuditLog.stage == "strategist")
            )
            audit_res = await session.execute(audit_stmt)
            strat_audit = audit_res.scalar_one_or_none()
            assert strat_audit is not None
            assert strat_audit.payload["guardrail_checks_passed"] is True

        await session.commit()

@pytest.mark.asyncio
async def test_strategist_guardrail_blocks_exhausted_retries():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_exhausted_{test_run_id}",
            customer_id=f"cust_exhausted_{test_run_id}",
            amount=2000.0,
            currency="INR",
            status="diagnosed"
        )
        session.add(case)
        await session.flush()

        await session.execute(delete(Decision).where(Decision.case_id == case.id))
        await session.execute(delete(Diagnosis).where(Diagnosis.case_id == case.id))
        await session.flush()

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause="issuer_timeout",
            confidence=1.0,
            evidence={"source": "unit_test"},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()

        prior_decision = Decision(
            case_id=case.id,
            diagnosis_id=diagnosis.id,
            chosen_action="immediate_single_retry",
            justification="Previous attempt",
            policy_rule_id="POL_ISSUER_TIMEOUT",
            guardrail_checks_passed=True
        )
        session.add(prior_decision)
        await session.flush()

        strategist = StrategistService(session, kill_switch_active=False)
        blocked_decision = await strategist.decide_single_case(case.id)

        assert blocked_decision is not None
        assert blocked_decision.guardrail_checks_passed is False
        assert blocked_decision.chosen_action == "escalate_or_stop_by_policy"
        assert "MAX_RETRIES_EXCEEDED" in blocked_decision.justification or "exceeded" in blocked_decision.justification
        assert case.status == "stopped_by_policy"

        await session.commit()

@pytest.mark.asyncio
async def test_strategist_guardrail_kill_switch():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_kill_{test_run_id}",
            customer_id=f"cust_kill_{test_run_id}",
            amount=3000.0,
            currency="INR",
            status="diagnosed"
        )
        session.add(case)
        await session.flush()

        await session.execute(delete(Decision).where(Decision.case_id == case.id))
        await session.execute(delete(Diagnosis).where(Diagnosis.case_id == case.id))
        await session.flush()

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause="insufficient_funds",
            confidence=1.0,
            evidence={"source": "unit_test"},
            method=DiagnosisMethod.rule
        )
        session.add(diagnosis)
        await session.flush()

        strategist = StrategistService(session, kill_switch_active=True)
        decision = await strategist.decide_single_case(case.id)

        assert decision is not None
        assert decision.guardrail_checks_passed is False
        assert decision.chosen_action == "escalate_or_stop_by_policy"
        assert "GLOBAL_KILL_SWITCH_ACTIVE" in decision.justification or "kill switch" in decision.justification
        await session.commit()
