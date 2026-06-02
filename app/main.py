from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import engine

from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.patients.router import router as patients_router
from app.api.v1.appointments.router import router as appointment_router
from app.api.v1.queue.router import router as queue_router
from app.api.v1.encounters.router import router as encounter_router

from app.api.super_admin.auth.router import router as super_admin_auth_router

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(patients_router, prefix=settings.API_PREFIX)
app.include_router(appointment_router, prefix=settings.API_PREFIX)
app.include_router(queue_router, prefix=settings.API_PREFIX)
app.include_router(encounter_router, prefix=settings.API_PREFIX)

app.include_router(super_admin_auth_router, prefix=settings.API_PREFIX)
@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request, name="landing/index.html")

@app.get("/healthz")
async def read_root() -> dict[str, str]:
    return {"status": "ok"}
