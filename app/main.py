from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/healthz")
async def read_root() -> dict[str, str]:
    return {"status": "ok"}
