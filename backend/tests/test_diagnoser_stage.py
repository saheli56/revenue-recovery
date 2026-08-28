import pytest
import uuid
from sqlalchemy import select, and_
from database import async_session_factory
from models import RecoveryCase, Diagnosis, AuditLog, CaseType, DiagnosisMethod
from pipeline.diagnoser import DiagnoserService

@pytest.mark.asyncio
async def test_diagnoser_deterministic_rules():
    test_run_id = uuid.uuid4().hex[:6]
    test_cases = [
        ("insufficient_funds", CaseType.payment_failure, "insufficient_funds", 1.0),
        ("card_expired", CaseType.payment_failure, "card_expired", 1.0),
        ("issuer_timeout", CaseType.payment_failure, "issuer_timeout", 1.0),
        ("authentication_failed", CaseType.payment_failure, "authentication_failed", 1.0),
        ("gateway_declined", CaseType.payment_failure, "gateway_declined", 1.0),
    ]

    async with async_session_factory() as session:
        for idx, (err_code, ctype, expected_cause, expected_conf) in enumerate(test_cases):
            case = RecoveryCase(
                case_type=ctype,
                source_reference=f"txn_rule_{test_run_id}_{idx}",
                customer_id=f"cust_rule_{test_run_id}",
                amount=1999.0,
                currency="INR",
                status="detected_at_risk"
            )
            session.add(case)
            await session.flush()

            ingest_audit = AuditLog(
                case_id=case.id,
                stage="ingestion",
                event="raw_event_received",
                payload={"error_code": err_code, "customer_note": "Normal standard note"}
            )
            session.add(ingest_audit)
            await session.flush()

            diagnoser = DiagnoserService(session)
            diagnosis = await diagnoser.diagnose_single_case(case.id)

            assert diagnosis is not None
            assert diagnosis.root_cause == expected_cause
            assert diagnosis.confidence == expected_conf
            assert diagnosis.method == DiagnosisMethod.rule

            audit_stmt = select(AuditLog).where(
                and_(AuditLog.case_id == case.id, AuditLog.stage == "diagnoser")
            )
            audit_res = await session.execute(audit_stmt)
            diag_audit = audit_res.scalar_one_or_none()
            assert diag_audit is not None
            assert diag_audit.event == "diagnosis_completed"
            assert diag_audit.payload["method"] == "rule"

        await session.commit()

@pytest.mark.asyncio
async def test_diagnoser_llm_fallback_on_ambiguity():
    test_run_id = uuid.uuid4().hex[:6]
    ambiguous_payloads = [
        {"customer_note": "Paise cut gaye par order nahi mila urgent check karo", "error_code": "BAD_REQUEST_ERROR"},
        {"customer_note": "Bhai OTP der se aaya tha timeout ho gaya", "error_code": "unknown"}
    ]

    async with async_session_factory() as session:
        for idx, payload in enumerate(ambiguous_payloads):
            case = RecoveryCase(
                case_type=CaseType.payment_failure,
                source_reference=f"txn_llm_{test_run_id}_{idx}",
                customer_id=f"cust_llm_{test_run_id}",
                amount=2499.0,
                currency="INR",
                status="detected_at_risk"
            )
            session.add(case)
            await session.flush()

            ingest_audit = AuditLog(
                case_id=case.id,
                stage="ingestion",
                event="raw_event_received",
                payload=payload
            )
            session.add(ingest_audit)
            await session.flush()

            diagnoser = DiagnoserService(session)
            diagnosis = await diagnoser.diagnose_single_case(case.id)

            assert diagnosis is not None
            assert diagnosis.method == DiagnosisMethod.llm
            assert diagnosis.confidence >= 0.60
            assert "signals_used" in diagnosis.evidence

            persisted_diag = await session.get(Diagnosis, diagnosis.id)
            assert persisted_diag is not None
            assert persisted_diag.case_id == case.id

        await session.commit()
