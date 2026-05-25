from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine

from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.patients.router import router as patients_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan function to create database tables on startup."""
    yield
    # shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(patients_router, prefix=settings.API_PREFIX)

@app.get("/healthz")
async def read_root() -> dict[str, str]:
    return {"status": "ok"}
