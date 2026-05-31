# Dental Saas Backend

## Overview

This repository contains the backend for a dental practice management SaaS application built with FastAPI and SQLAlchemy. The backend provides tenant-aware authentication, patient management, appointment and queue handling, encounters, and user administration.

## Key Features

- JWT-based authentication and refresh token support
- Tenant-aware multi-tenant architecture
- Patient registration, history, and medical records
- Appointment booking, rescheduling, confirmation, and status tracking
- Live queue management for dentists and receptionists
- User and role management
- Async SQLAlchemy database access with PostgreSQL
- API documentation via Swagger UI and ReDoc
- Docker Compose support for local development

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy Async ORM
- Alembic for migrations
- PostgreSQL
- Redis
- PyJWT
- Pydantic / Pydantic Settings

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd dental-saas-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env.dev` file in the project root with values similar to the example below:

```env
DATABASE_URL=postgresql+asyncpg://<postgresuser>:<password>@localhost:5432/dental_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your_super_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DEBUG=True
ENV=dev
```

> The application uses `app/core/config.py` to load settings from `.env.dev` by default.

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- `http://localhost:8000/docs` for Swagger UI
- `http://localhost:8000/redoc` for ReDoc
- `http://localhost:8000/healthz` for health checks

## Docker Development

The repository includes a `docker-compose.yml` file for local development.

```bash
docker compose up --build
```

This starts:

- `app` on port `8000`
- `db` PostgreSQL service on port `5432`
- `redis` on port `6379`

## API Base URL

All API routes are prefixed with `/api/v1` as configured in `app/core/config.py`.

Example endpoints:

- `POST /api/v1/auth/register-tenant`
- `POST /api/v1/auth/token`
- `GET /api/v1/auth/me`
- `GET /api/v1/patients`
- `POST /api/v1/appointments`
- `GET /api/v1/queue/today`

## Authentication

- The app uses JWT bearer tokens.
- Login is available at `/api/v1/auth/token`.
- Send `Authorization: Bearer <access_token>` with protected requests.

## Project Structure

- `app/main.py` — FastAPI application startup and router registration
- `app/core/` — configuration, database, security, and dependencies
- `app/api/v1/` — API routers and route definitions
- `app/models/` — SQLAlchemy ORM models
- `app/schemas/` — Pydantic request and response schemas
- `app/services/` — business logic services
- `app/templates/` — Jinja2 landing page templates
- `alembic/` — database migrations
- `docs/` — API reference and design documentation

## Database

- PostgreSQL is the recommended database.
- Async SQLAlchemy is configured in `app/core/database.py`.
- Use Alembic for schema migrations.

## Notes

- There is a landing page route at `/` that renders `app/templates/landing/index.html`.
- A local health endpoint is available at `/healthz`.
- Detailed route documentation can be found in `docs/buddha_dental_api.md`.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Run tests and make sure the API works locally.
4. Submit a pull request.

## License

This project does not include a license file. Add one as needed.
