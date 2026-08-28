import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from sqlalchemy import select
from models import RecoveryCase, Outcome

async def main():
    async with async_session_factory() as session:
        c = (await session.execute(select(RecoveryCase.id))).scalars().all()
        o = (await session.execute(select(Outcome.case_id, Outcome.recovered))).all()
        print('Cases count:', len(c), 'First 5 case IDs:', c[:5])
        print('Outcomes count:', len(o), 'First 5 outcome case IDs:', o[:5])

if __name__ == "__main__":
    asyncio.run(main())
