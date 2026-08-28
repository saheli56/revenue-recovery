import asyncio
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.executor import ExecutorService
from models import Execution

async def execute_executor_stage():
    async with async_session_factory() as session:
        executor = ExecutorService(session)
        executions: List[Execution] = await executor.run_executor_batch()

    total = len(executions)
    channel_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}

    for ex in executions:
        channel_counts[ex.channel] = channel_counts.get(ex.channel, 0) + 1
        status_counts[ex.status] = status_counts.get(ex.status, 0) + 1

    print("\n=======================================================")
    print(f"        EXECUTOR STAGE EXECUTION REPORT ({total} CASES)")
    print("=======================================================")
    print(f"Total Execution Dispatches  : {total}")
    print("-------------------------------------------------------")
    print("Channel Execution Breakdown:")
    for ch, count in sorted(channel_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {ch:<35}: {count:3d} ({(count / max(total, 1)) * 100:5.1f}%)")
    print("-------------------------------------------------------")
    print("Execution Statuses & Delivery Receipts:")
    for st, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {st:<35}: {count:3d}")
    print("=======================================================\n")
    return executions

if __name__ == "__main__":
    asyncio.run(execute_executor_stage())
