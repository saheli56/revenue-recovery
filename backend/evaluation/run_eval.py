import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from evaluation.harness import EvaluationHarness, print_evaluation_summary

async def main():
    async with async_session_factory() as session:
        harness = EvaluationHarness(session)
        report = await harness.generate_report()
        print_evaluation_summary(report)

if __name__ == "__main__":
    asyncio.run(main())
