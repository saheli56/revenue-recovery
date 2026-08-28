import json
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, delete
from database import async_session_factory
from models import RecoveryCase, Diagnosis, Decision, Execution, Outcome, AuditLog, CaseType
from datagen.generator import export_and_print_dataset

async def load_synthetic_dataset_into_db(records: List[Dict[str, Any]], session=None) -> int:
    inserted_count = 0
    
    async def _insert_records(sess):
        count = 0
        for item in records:
            created_at_dt = datetime.fromisoformat(item["created_at"])
            case = RecoveryCase(
                case_type=CaseType(item["case_type"]),
                source_reference=item["source_reference"],
                customer_id=item["customer_id"],
                amount=float(item["amount"]),
                currency=item.get("currency", "INR"),
                status="open",
                created_at=created_at_dt
            )
            sess.add(case)
            await sess.flush()

            audit = AuditLog(
                case_id=case.id,
                stage="ingestion",
                event="raw_event_received",
                payload=item,
                timestamp=created_at_dt
            )
            sess.add(audit)
            count += 1
        return count

    if session is not None:
        inserted_count = await _insert_records(session)
    else:
        async with async_session_factory() as sess:
            inserted_count = await _insert_records(sess)
            await sess.commit()

    return inserted_count

async def load_synthetic_batch_into_db(dataset_path: str = None, clear_existing: bool = False) -> int:
    if dataset_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dataset_path = os.path.join(base_dir, "data", "synthetic_batch.json")

    if not os.path.exists(dataset_path):
        records = export_and_print_dataset(dataset_path)
    else:
        with open(dataset_path, "r", encoding="utf-8") as f:
            records = json.load(f)

    inserted_count = 0

    async with async_session_factory() as session:
        if clear_existing:
            await session.execute(delete(Outcome))
            await session.execute(delete(Execution))
            await session.execute(delete(Decision))
            await session.execute(delete(Diagnosis))
            await session.execute(delete(AuditLog))
            await session.execute(delete(RecoveryCase))
            await session.commit()

        inserted_count = await load_synthetic_dataset_into_db(records, session)
        await session.commit()

    print(f"Database Loader: Successfully loaded {inserted_count} recovery cases and audit events into database.")
    return inserted_count

if __name__ == "__main__":
    asyncio.run(load_synthetic_batch_into_db(clear_existing=True))
