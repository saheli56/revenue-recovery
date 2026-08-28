import pytest
import uuid
from sqlalchemy import select, and_
from database import async_session_factory
from models import RecoveryCase, AuditLog, CaseType
from pipeline.detector import DetectorService

@pytest.mark.asyncio
async def test_detector_qualifies_valid_at_risk_cases():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case = RecoveryCase(
            case_type=CaseType.payment_failure,
            source_reference=f"txn_valid_{test_run_id}",
            customer_id=f"cust_{test_run_id}",
            amount=1499.0,
            currency="INR",
            status="open"
        )
        session.add(case)
        await session.flush()

        ingest_audit = AuditLog(
            case_id=case.id,
            stage="ingestion",
            event="raw_event_received",
            payload={
                "is_fraud_flagged": False,
                "is_already_refunded": False,
                "is_duplicate": False,
                "error_code": "insufficient_funds"
            }
        )
        session.add(ingest_audit)
        await session.commit()

        detector = DetectorService(session)
        result = await detector.detect_single_case(case.id)
        await session.commit()

        assert result is not None
        assert result.is_at_risk is True
        assert result.is_excluded is False
        assert result.exclusion_reason is None

        audit_stmt = select(AuditLog).where(
            and_(AuditLog.case_id == case.id, AuditLog.stage == "detector")
        )
        audit_res = await session.execute(audit_stmt)
        detector_audit = audit_res.scalar_one_or_none()
        assert detector_audit is not None
        assert detector_audit.event == "case_qualified_at_risk"
        assert detector_audit.payload["decision"] == "qualified"

@pytest.mark.asyncio
async def test_detector_excludes_disqualified_cases():
    test_run_id = uuid.uuid4().hex[:6]
    test_scenarios = [
        ({"is_fraud_flagged": True, "is_already_refunded": False, "is_duplicate": False}, "FRAUD_DISQUALIFIED"),
        ({"is_fraud_flagged": False, "is_already_refunded": True, "is_duplicate": False}, "REFUND_DISQUALIFIED"),
        ({"is_fraud_flagged": False, "is_already_refunded": False, "is_duplicate": True}, "DUPLICATE_DISQUALIFIED")
    ]

    async with async_session_factory() as session:
        for idx, (flags, expected_prefix) in enumerate(test_scenarios):
            case = RecoveryCase(
                case_type=CaseType.checkout_abandonment,
                source_reference=f"txn_disq_{test_run_id}_{idx}",
                customer_id=f"cust_disq_{test_run_id}",
                amount=999.0,
                currency="INR",
                status="open"
            )
            session.add(case)
            await session.flush()

            ingest_audit = AuditLog(
                case_id=case.id,
                stage="ingestion",
                event="raw_event_received",
                payload=flags
            )
            session.add(ingest_audit)
            await session.flush()

            detector = DetectorService(session)
            res = await detector.detect_single_case(case.id)
            assert res is not None
            assert res.is_at_risk is False
            assert res.is_excluded is True
            assert expected_prefix in res.exclusion_reason

            audit_stmt = select(AuditLog).where(
                and_(AuditLog.case_id == case.id, AuditLog.stage == "detector")
            )
            audit_res = await session.execute(audit_stmt)
            detector_audit = audit_res.scalar_one_or_none()
            assert detector_audit is not None
            assert detector_audit.event == "case_excluded_from_recovery"
            assert detector_audit.payload["decision"] == "excluded"

        await session.commit()
