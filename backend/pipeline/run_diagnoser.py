import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.diagnoser import DiagnoserService

async def main():
    async with async_session_factory() as session:
        diagnoser = DiagnoserService(session)
        print("Starting Diagnoser Stage Batch Run...")
        diagnoses = await diagnoser.run_diagnoser_batch()

        total = len(diagnoses)
        rule_count = sum(1 for d in diagnoses if d.method.value == "rule")
        llm_count = sum(1 for d in diagnoses if d.method.value == "llm")
        avg_confidence = (
            sum(d.confidence for d in diagnoses) / max(total, 1)
        )

        print("\n=======================================================")
        print("           DIAGNOSER STAGE EXECUTION REPORT            ")
        print("=======================================================")
        print(f"Total Cases Diagnosed         : {total:3d}")
        print(f"Deterministic Rule Matches    : {rule_count:3d} ({(rule_count / max(total, 1)) * 100:5.1f}%)")
        print(f"AI Model Fallback Diagnoses   : {llm_count:3d} ({(llm_count / max(total, 1)) * 100:5.1f}%)")
        print(f"Average Diagnosis Confidence  : {avg_confidence * 100:5.1f}%")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
