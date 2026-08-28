import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.auditor import AuditorService

async def main():
    async with async_session_factory() as session:
        auditor = AuditorService(session)
        for i in range(1, 15):
            res = await auditor.verify_unbroken_audit_trail(i)
            print(f"Case {i}: {res}")

if __name__ == "__main__":
    asyncio.run(main())
