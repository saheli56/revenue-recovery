from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database import engine, Base
from api.cases import router as cases_router
from api.analytics import router as analytics_router
from api.policies import router as policies_router
from datagen.generator import generate_synthetic_dataset
from datagen.loader import load_synthetic_dataset_into_db
from database import async_session_factory
from pipeline.detector import DetectorService
from pipeline.diagnoser import DiagnoserService
from pipeline.strategist import StrategistService
from pipeline.executor import ExecutorService
from pipeline.tracker import OutcomeTrackerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        dataset = generate_synthetic_dataset(total_cases=150, random_seed=42)
        async with async_session_factory() as session:
            await load_synthetic_dataset_into_db(dataset, session)
            
            detector = DetectorService(session)
            await detector.run_detector_batch()
            
            diagnoser = DiagnoserService(session)
            await diagnoser.run_diagnoser_batch()
            
            strategist = StrategistService(session)
            await strategist.run_strategist_batch()
            
            executor = ExecutorService(session)
            await executor.run_executor_batch()
            
            tracker = OutcomeTrackerService(session)
            await tracker.resolve_outcomes_batch()
    except Exception:
        pass
        
    yield
    await engine.dispose()

app = FastAPI(
    title="AI Revenue Recovery Engine",
    description="Autonomous Agentic Revenue Recovery & Dunning Engine for Payment Failures, Cart Abandonment, and Recurring Subscriptions.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "revenue-recovery-engine",
        "environment": settings.ENVIRONMENT,
        "kill_switch_active": settings.GLOBAL_KILL_SWITCH
    }

app.include_router(cases_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
