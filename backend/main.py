from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database import engine, Base
from api.cases import router as cases_router
from api.analytics import router as analytics_router
from api.policies import router as policies_router
from datagen.loader import load_synthetic_batch_into_db
from database import async_session_factory
from pipeline.detector import DetectorService
from pipeline.diagnoser import DiagnoserService
from pipeline.strategist import StrategistService
from pipeline.executor import ExecutorService
import asyncio
from pipeline.tracker import OutcomeTrackerService

async def _background_initial_warmup():
    try:
        await load_synthetic_batch_into_db(clear_existing=False)
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
    except Exception as exc:
        print(f"Background warmup error: {exc}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Launch warmup in background so Uvicorn binds to the PORT immediately on deployment
    asyncio.create_task(_background_initial_warmup())
        
    yield
    await engine.dispose()

app = FastAPI(
    title="AI Revenue Recovery Engine",
    description="Autonomous Agentic Revenue Recovery & Dunning Engine for Payment Failures, Cart Abandonment, and Recurring Subscriptions.",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def custom_cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        try:
            response = await call_next(request)
        except Exception as exc:
            response = Response(content=f'{{"detail": "{str(exc)}"}}', status_code=500, media_type="application/json")

    origin = request.headers.get("origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
