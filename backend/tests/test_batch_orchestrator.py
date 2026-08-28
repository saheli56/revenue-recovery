import pytest
import uuid
from sqlalchemy import select
from database import async_session_factory
from models import RecoveryCase, AuditLog, CaseType
from orchestrator.pipeline_runner import BatchOrchestrator

@pytest.mark.asyncio
async def test_batch_orchestrator_concurrency_execution():
    test_run_id = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        case_ids = []
        for i in range(5):
            case = RecoveryCase(
                case_type=CaseType.payment_failure,
                source_reference=f"txn_batch_{test_run_id}_{i}",
                customer_id=f"cust_batch_{test_run_id}_{i}",
                amount=1999.0,
                currency="INR",
                status="open"
            )
            session.add(case)
            await session.flush()
            case_ids.append(case.id)

            audit = AuditLog(
                case_id=case.id,
                stage="ingestion",
                event="raw_event_received",
                payload={"error_code": "card_expired", "is_fraud_flagged": False}
            )
            session.add(audit)

        await session.commit()

    orchestrator = BatchOrchestrator(max_concurrency=3)
    results = [await orchestrator.process_single_case_pipeline(cid) for cid in case_ids]

    assert len(results) == 5
    for r in results:
        assert r.final_status in ["recovered", "failed", "stopped_by_policy", "escalated"]
        assert len(r.stages_completed) >= 2

@pytest.mark.asyncio
async def test_batch_orchestrator_error_isolation():
    orchestrator = BatchOrchestrator(max_concurrency=2)
    invalid_case_id = 999999999
    res = await orchestrator.process_single_case_pipeline(invalid_case_id)

    assert res.final_status == "not_found"
    assert res.error is not None
