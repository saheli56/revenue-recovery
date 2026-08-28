import pytest
import os
import uuid
import json
from sqlalchemy import select
from database import async_session_factory
from models import RecoveryCase, AuditLog, CaseType
from datagen.config import DatasetDistributionConfig
from datagen.generator import generate_synthetic_dataset
from datagen.loader import load_synthetic_batch_into_db

def test_generate_synthetic_dataset_defaults():
    config = DatasetDistributionConfig(total_records=120, seed=123)
    dataset = generate_synthetic_dataset(config)

    assert len(dataset) == 120
    case_types = {item["case_type"] for item in dataset}
    assert "payment_failure" in case_types
    assert "checkout_abandonment" in case_types
    assert "subscription_failure" in case_types

    first_record = dataset[0]
    assert "source_reference" in first_record
    assert "customer_id" in first_record
    assert "amount" in first_record
    assert first_record["amount"] > 0
    assert "customer_note" in first_record
    assert "is_fraud_flagged" in first_record
    assert "is_already_refunded" in first_record
    assert "is_duplicate" in first_record

def test_generate_synthetic_dataset_reproducibility():
    config1 = DatasetDistributionConfig(total_records=50, seed=99)
    config2 = DatasetDistributionConfig(total_records=50, seed=99)
    data1 = generate_synthetic_dataset(config1)
    data2 = generate_synthetic_dataset(config2)

    assert [d["source_reference"] for d in data1] == [d["source_reference"] for d in data2]
    assert [d["amount"] for d in data1] == [d["amount"] for d in data2]

@pytest.mark.asyncio
async def test_dataset_loader_into_database(tmp_path):
    unique_run = uuid.uuid4().hex[:6]
    temp_json = str(tmp_path / f"test_batch_{unique_run}.json")
    computed_seed = int(unique_run, 16) % 100000
    config = DatasetDistributionConfig(total_records=20, seed=computed_seed)
    records = generate_synthetic_dataset(config)

    for item in records:
        item["source_reference"] = f"test_{unique_run}_{item['source_reference']}"

    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(records, f)

    inserted = await load_synthetic_batch_into_db(dataset_path=temp_json, clear_existing=False)
    assert inserted == 20

    async with async_session_factory() as session:
        sample_ref = records[0]["source_reference"]
        stmt = select(RecoveryCase).where(RecoveryCase.source_reference == sample_ref)
        res = await session.execute(stmt)
        case_obj = res.scalar_one_or_none()
        assert case_obj is not None
        assert case_obj.amount == records[0]["amount"]

        audit_stmt = select(AuditLog).where(AuditLog.case_id == case_obj.id)
        audit_res = await session.execute(audit_stmt)
        audit_log = audit_res.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.stage == "ingestion"
        assert audit_log.event == "raw_event_received"
