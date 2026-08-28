import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import engine, Base
from datagen.loader import load_synthetic_batch_into_db
from pipeline.detector import DetectorService
from pipeline.diagnoser import DiagnoserService
from pipeline.strategist import StrategistService
from pipeline.executor import ExecutorService
from pipeline.tracker import OutcomeTrackerService
from database import async_session_factory

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await load_synthetic_batch_into_db(clear_existing=True)
    
    async with async_session_factory() as session:
        detector = DetectorService(session)
        await detector.run_detection_batch()

        diagnoser = DiagnoserService(session)
        await diagnoser.run_diagnoser_batch()

        strategist = StrategistService(session)
        await strategist.run_strategist_batch()

        executor = ExecutorService(session)
        await executor.run_executor_batch()

        tracker = OutcomeTrackerService(session)
        await tracker.run_tracker_batch()
    
    await engine.dispose()
    print("Database successfully initialized and seeded with 150 resolved baseline cases.")

if __name__ == "__main__":
    asyncio.run(main())
