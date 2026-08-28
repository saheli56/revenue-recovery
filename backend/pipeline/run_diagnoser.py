import asyncio
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.diagnoser import DiagnoserService
from models import Diagnosis

async def execute_diagnoser_stage():
    async with async_session_factory() as session:
        diagnoser = DiagnoserService(session)
        diagnoses: List[Diagnosis] = await diagnoser.run_diagnoser_batch()

    total = len(diagnoses)
    rule_count = sum(1 for d in diagnoses if d.method.value == "rule")
    llm_count = sum(1 for d in diagnoses if d.method.value == "llm")
    avg_confidence = sum(d.confidence for d in diagnoses) / max(total, 1)

    root_cause_counts: Dict[str, int] = {}
    for d in diagnoses:
        root_cause_counts[d.root_cause] = root_cause_counts.get(d.root_cause, 0) + 1

    print("\n=======================================================")
    print(f"        DIAGNOSER STAGE EXECUTION REPORT ({total} CASES)")
    print("=======================================================")
    print(f"Total Diagnoses Created     : {total}")
    print(f"Deterministic Rule Method   : {rule_count:3d} ({(rule_count / max(total, 1)) * 100:5.1f}%)")
    print(f"Anthropic LLM Fallback      : {llm_count:3d} ({(llm_count / max(total, 1)) * 100:5.1f}%)")
    print(f"Average Confidence Score    : {avg_confidence:.2f} / 1.00")
    print("-------------------------------------------------------")
    print("Root Cause Breakdown:")
    for cause, count in sorted(root_cause_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cause:<40}: {count:3d}")
    print("=======================================================\n")
    return diagnoses

if __name__ == "__main__":
    asyncio.run(execute_diagnoser_stage())
