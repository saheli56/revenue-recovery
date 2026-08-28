import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datagen.loader import load_synthetic_batch_into_db
from orchestrator.pipeline_runner import BatchOrchestrator, BatchExecutionSummary

def parse_args():
    parser = argparse.ArgumentParser(description="AI Revenue Recovery Engine - Batch Orchestration Runner")
    parser.add_argument("--batch-id", type=str, default="BATCH_PROD_001", help="Batch identifier")
    parser.add_argument("--concurrency", type=int, default=5, help="Maximum concurrent worker tasks")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to process")
    parser.add_argument("--seed-fresh", action="store_true", help="Reload fresh dataset before running")
    return parser.parse_args()

async def main():
    args = parse_args()

    print("\n=================================================================")
    print("      AI REVENUE RECOVERY ENGINE - BATCH ORCHESTRATOR")
    print(f"      Batch ID: {args.batch_id} | Concurrency Workers: {args.concurrency}")
    print("=================================================================\n")

    if args.seed_fresh:
        print("[Orchestrator] Seeding fresh synthetic batch into database...")
        await load_synthetic_batch_into_db(clear_existing=True)

    print("[Orchestrator] Dispatching cases through 5-stage pipeline...")
    orchestrator = BatchOrchestrator(max_concurrency=args.concurrency)
    summary: BatchExecutionSummary = await orchestrator.run_batch(limit=args.limit)

    recovery_rate = (summary.total_recovered_amount / max(summary.total_at_risk_amount, 1.0)) * 100.0

    print("\n=================================================================")
    print(f"               BATCH RUN COMPLETE ({summary.processed_count}/{summary.total_cases} CASES)")
    print("=================================================================")
    print(f"Total Gross Value at Risk   : INR {summary.total_at_risk_amount:,.2f}")
    print(f"Total Successfully Recovered : INR {summary.total_recovered_amount:,.2f}")
    print(f"Net Recovery Percentage      : {recovery_rate:5.1f}%")
    print(f"Total Processing Time        : {summary.elapsed_seconds:.2f} seconds")
    print("-----------------------------------------------------------------")
    print("Case Final Status Breakdown:")
    for status, count in sorted(summary.status_breakdown.items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(summary.processed_count, 1)) * 100.0
        print(f"  - {status:<30}: {count:3d} cases ({pct:5.1f}%)")
    print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
