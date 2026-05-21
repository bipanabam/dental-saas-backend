from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine


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

@app.get("/healthz")
async def read_root() -> dict[str, str]:
    return {"status": "ok"}
