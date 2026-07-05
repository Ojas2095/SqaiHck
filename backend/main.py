from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from core.config import settings
from database import engine, Base
from routers import ehr, treatments, patients, dashboard

app = FastAPI(title=settings.PROJECT_NAME, version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup database tables on startup (In production, use Alembic instead)
@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

# Include Modular Routers
app.include_router(ehr.router, prefix=settings.API_V1_STR)
app.include_router(treatments.router, prefix=settings.API_V1_STR)
app.include_router(patients.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "AYUSH AI Enterprise Platform (V3 Modular)", "status": "online"}

