import asyncio
import sys
import os
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.detector import DetectorService, DetectionResult

async def execute_detector_stage():
    async with async_session_factory() as session:
        detector = DetectorService(session)
        results: List[DetectionResult] = await detector.run_detection_batch()

    total = len(results)
    qualified = [r for r in results if r.is_at_risk]
    excluded = [r for r in results if r.is_excluded]

    gross_at_risk_amount = sum(r.amount for r in qualified)
    excluded_amount = sum(r.amount for r in excluded)

    print("\n=======================================================")
    print(f"        DETECTOR STAGE EXECUTION REPORT ({total} CASES)")
    print("=======================================================")
    print(f"Total Evaluated Cases       : {total}")
    print(f"Genuine At-Risk Qualified   : {len(qualified):3d} (INR {gross_at_risk_amount:,.2f})")
    print(f"Disqualified & Excluded     : {len(excluded):3d} (INR {excluded_amount:,.2f})")
    print("-------------------------------------------------------")
    print("Breakdown of Excluded Cases by Reason:")

    exclusion_breakdown = {}
    for ex in excluded:
        reason = ex.exclusion_reason or "Unknown"
        exclusion_breakdown[reason] = exclusion_breakdown.get(reason, 0) + 1

    for reason, count in exclusion_breakdown.items():
        print(f"  - {reason:<60}: {count:2d}")

    print("=======================================================\n")
    return results

if __name__ == "__main__":
    asyncio.run(execute_detector_stage())
