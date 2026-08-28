import asyncio
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from database import async_session_factory
from pipeline.tracker import OutcomeTrackerService
from pipeline.auditor import AuditorService
from models import Outcome, RecoveryCase

async def execute_tracker_stage():
    async with async_session_factory() as session:
        tracker = OutcomeTrackerService(session)
        outcomes: List[Outcome] = await tracker.run_tracker_batch()

        auditor = AuditorService(session)
        sample_outcomes_stmt = (
            select(Outcome.case_id)
            .order_by(Outcome.id.desc())
            .limit(10)
        )
        sample_res = await session.execute(sample_outcomes_stmt)
        sample_case_ids = sample_res.scalars().all()

        verification_sample = []
        for cid in sample_case_ids:
            v = await auditor.verify_unbroken_audit_trail(cid)
            verification_sample.append(v)

    total = len(outcomes)
    recovered_cases = [o for o in outcomes if o.recovered]
    total_recovered_amount = sum(o.recovered_amount or 0.0 for o in recovered_cases)

    status_counts: Dict[str, int] = {}
    for o in outcomes:
        status_counts[o.final_status.value] = status_counts.get(o.final_status.value, 0) + 1

    print("\n=======================================================")
    print(f"        OUTCOME TRACKER & AUDITOR REPORT ({total} CASES)")
    print("=======================================================")
    print(f"Total Outcomes Resolved     : {total}")
    print(f"Total Successfully Recovered: {len(recovered_cases):3d} (INR {total_recovered_amount:,.2f})")
    print(f"Gross Recovery Rate         : {(len(recovered_cases) / max(total, 1)) * 100:5.1f}%")
    print("-------------------------------------------------------")
    print("Final Status Breakdown:")
    for st, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(total, 1)) * 100
        print(f"  - {st:<30}: {count:3d} ({pct:5.1f}%)")
    print("-------------------------------------------------------")
    print("Audit Trail Verification on Completed Cases Sample:")
    all_valid = len(verification_sample) > 0 and all(v["valid"] for v in verification_sample)
    print(f"  - Unbroken Audit Trails Verified: {'PASSED (100% Intact Chain)' if all_valid else 'FAILED'}")
    print("=======================================================\n")
    return outcomes

if __name__ == "__main__":
    asyncio.run(execute_tracker_stage())
