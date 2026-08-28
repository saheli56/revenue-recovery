from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database import engine
from api.cases import router as cases_router
from api.analytics import router as analytics_router
from api.policies import router as policies_router

@asynccontextmanager
async def lifespan(app: FastAPI):
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
