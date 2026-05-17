# PHASE 00 — Project Setup & Foundation

## Phase Goal
Establish the complete monorepo structure, tooling, local development environment, and CI/CD skeleton so every subsequent phase has a clean, consistent base to build upon. No features are built here — only infrastructure and conventions are locked in.

---

## Features Implemented
- Monorepo directory structure (frontend + backend side-by-side)
- Backend: FastAPI project skeleton with async support
- Frontend: Next.js 14 (App Router) project skeleton with Tailwind v4 + Shadcn UI
- Environment variable management (`.env` per service)
- Git repository initialization with `.gitignore` and branch strategy
- Pre-commit hooks (Black, isort, ESLint, Prettier)
- Docker Compose for local development (FastAPI + MongoDB)
- README with local setup instructions

---

## Technical Architecture

```
ai-career-platform/              ← Monorepo root
├── backend/                     ← FastAPI service
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    ← Next.js 14 App Router
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docs/                        ← All phase .md files live here
├── docker-compose.yml
├── .gitignore
├── .pre-commit-config.yaml
└── README.md
```

---

## Folder Structure (Backend)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  ← FastAPI app entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            ← Pydantic Settings (env vars)
│   │   ├── database.py          ← MongoDB Motor connection
│   │   └── exceptions.py        ← Global exception handlers
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py        ← Main v1 router
│   ├── models/                  ← Pydantic request/response models
│   ├── services/                ← Business logic
│   ├── repositories/            ← DB queries (data access layer)
│   └── utils/
│       ├── __init__.py
│       └── logger.py            ← structlog setup
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Folder Structure (Frontend)

```
frontend/
├── src/
│   ├── app/                     ← Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx             ← Landing page
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                  ← Shadcn UI components
│   │   └── shared/              ← App-wide shared components
│   ├── lib/
│   │   ├── api.ts               ← Axios/fetch API client
│   │   └── utils.ts
│   ├── hooks/                   ← Custom React hooks
│   ├── types/                   ← TypeScript interfaces
│   └── store/                   ← Zustand state store
├── public/
├── tailwind.config.ts
├── tsconfig.json
├── next.config.ts
├── package.json
└── .env.example
```

---

## Database Collections / Schema
None — MongoDB connection is wired but no collections exist yet.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Detailed health (DB ping) |

---

## Backend Tasks

### 1. FastAPI Skeleton (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import connect_db, close_db
from app.api.v1.router import api_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="AI Career Visibility Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-career-platform-backend"}
```

### 2. Config (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Career Platform"
    DEBUG: bool = False
    SECRET_KEY: str
    
    # Database
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "ai_career_platform"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # AI Provider
    LLM_PROVIDER: str = "huggingface"  # huggingface | gemini | gpt
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

### 3. Database (`app/core/database.py`)
```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_db():
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.MONGODB_DB_NAME]
    # Verify connection
    await db_instance.client.admin.command('ping')
    print("✅ MongoDB connected")

async def close_db():
    if db_instance.client:
        db_instance.client.close()
        print("✅ MongoDB disconnected")

def get_db():
    return db_instance.db
```

### 4. Structured Logger (`app/utils/logger.py`)
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()
```

### 5. Global Exception Handler (`app/core/exceptions.py`)
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message}
    )
```

---

## Frontend Tasks

### 1. Initialize Next.js 14 with App Router
```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"
```

### 2. Install Shadcn UI
```bash
cd frontend
npx shadcn-ui@latest init
# Choose: Default style, Slate base color, CSS variables
```

### 3. Install core dependencies
```bash
npm install axios zustand @tanstack/react-query lucide-react
npm install -D @types/node
```

### 4. API Client (`src/lib/api.ts`)
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// Request interceptor: attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
```

---

## AI Workflow Tasks
None in this phase.

---

## Scheduler / Background Tasks
None in this phase.

---

## Security Considerations
- `.env` files MUST be in `.gitignore` — never commit secrets
- `SECRET_KEY` must be a 32+ char random string
- CORS origins must be explicitly set, never `*` in production
- MongoDB URL must include authentication credentials

---

## Environment Variables

### Backend `.env.example`
```env
# App
APP_NAME=AI Career Platform
DEBUG=True
SECRET_KEY=your-super-secret-key-min-32-chars

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ai_career_platform

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# AI Provider
LLM_PROVIDER=huggingface
HUGGINGFACE_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
```

### Frontend `.env.example`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Third-Party Services Required
| Service | Purpose | Setup |
|---------|---------|-------|
| MongoDB (local Docker) | Database for local dev | `docker-compose up` |
| Node.js 18+ | Frontend runtime | `nvm install 18` |
| Python 3.11+ | Backend runtime | `pyenv install 3.11` |

---

## Docker Compose (`docker-compose.yml`)
```yaml
version: '3.9'

services:
  mongodb:
    image: mongo:7.0
    container_name: ai_career_mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_DATABASE: ai_career_platform

  backend:
    build: ./backend
    container_name: ai_career_backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    volumes:
      - ./backend:/app
    depends_on:
      - mongodb
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  mongodb_data:
```

---

## Backend `requirements.txt`
```
fastapi==0.111.0
uvicorn[standard]==0.30.1
motor==3.4.0
pydantic==2.7.1
pydantic-settings==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
structlog==24.2.0
httpx==0.27.0
slowapi==0.1.9
apscheduler==3.10.4
python-dotenv==1.0.1
```

---

## Implementation Steps (Exact Order)

1. `git init ai-career-platform && cd ai-career-platform`
2. Create directory structure as shown above
3. `cd backend && python -m venv venv && source venv/bin/activate`
4. `pip install -r requirements.txt`
5. Copy `.env.example` → `.env` and fill values
6. Create `app/main.py`, `app/core/config.py`, `app/core/database.py`
7. Create `app/utils/logger.py`, `app/core/exceptions.py`
8. Create `app/api/v1/router.py` (empty router for now)
9. Run: `uvicorn app.main:app --reload` → verify `/health` returns `{"status":"ok"}`
10. `cd ../frontend && npx create-next-app@latest .`
11. Install Shadcn, Axios, Zustand, React Query
12. Create `src/lib/api.ts`
13. Run: `npm run dev` → verify `http://localhost:3000` loads
14. `cd .. && docker-compose up -d mongodb` → verify MongoDB running
15. Test full `/health` endpoint → DB ping succeeds
16. Commit: `git commit -m "Phase 00: Project setup & foundation"`

---

## Testing Strategy

```python
# tests/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

## Edge Cases
- MongoDB connection failure on startup → app must fail fast with clear log
- Missing `.env` values → Pydantic Settings raises `ValidationError` immediately
- Port conflicts (8000 or 3000 in use) → change in docker-compose / next.config

---

## Deliverables / Checklist

- [ ] Monorepo directory structure created
- [ ] FastAPI app starts with `uvicorn`
- [ ] `/health` endpoint returns 200
- [ ] MongoDB connection verified via ping
- [ ] Next.js 14 app starts with `npm run dev`
- [ ] Shadcn UI initialized
- [ ] `api.ts` client created with interceptors
- [ ] Docker Compose runs MongoDB locally
- [ ] All `.env.example` files committed
- [ ] `.env` files in `.gitignore`
- [ ] Health check test passes
- [ ] `git commit` done

---

## Definition of Completion
Both `http://localhost:8000/health` and `http://localhost:3000` return successful responses. MongoDB connection is verified. All boilerplate is committed. The team can now clone the repo, run `docker-compose up` + both dev servers, and everything works without manual intervention.