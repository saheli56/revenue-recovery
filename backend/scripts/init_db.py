import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import engine, Base
from datagen.generator import generate_synthetic_dataset
from datagen.loader import load_synthetic_dataset_into_db
from database import async_session_factory

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    dataset = generate_synthetic_dataset(total_cases=150, random_seed=42)
    async with async_session_factory() as session:
        await load_synthetic_dataset_into_db(dataset, session)
    
    await engine.dispose()
    print("Database successfully initialized with synthetic baseline dataset.")

if __name__ == "__main__":
    asyncio.run(main())
