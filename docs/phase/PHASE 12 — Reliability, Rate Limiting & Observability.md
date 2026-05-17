# PHASE 12 — Reliability, Rate Limiting & Observability

## Phase Goal
Harden the production system. Add API-level rate limiting via `slowapi`, structured JSON logging via `structlog`, APScheduler health monitoring, LinkedIn token expiry alerting, and AI timeout guards. After this phase the system is production-observable and defensively coded.

---

## Features Implemented
- `slowapi` per-user rate limiting on all generation routes
- `structlog` structured JSON logging on all key events
- AI timeout guard (30s) with graceful error response
- LinkedIn token expiry pre-check before publish
- APScheduler misfire logging
- `GET /health` extended with scheduler + DB status
- Log event taxonomy defined
- Input sanitization on all text fields

---

## Technical Architecture

```
app/
├── core/
│   ├── rate_limit.py          ← slowapi limiter setup
│   └── timeout.py             ← asyncio timeout guard
├── utils/
│   └── logger.py              ← structlog structured JSON
├── middleware/
│   └── logging_middleware.py  ← Request/response logger
└── api/v1/routes/
    └── health.py              ← Extended health check
```

---

## Rate Limiting with slowapi (`app/core/rate_limit.py`)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

def get_user_identifier(request: Request) -> str:
    """Use JWT user_id if authenticated, else IP address."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return f"user:{payload['sub']}"
    return get_remote_address(request)

# Global limiter instance
limiter = Limiter(key_func=get_user_identifier)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "code": "API_RATE_LIMIT",
            "message": f"Too many requests. Limit: {exc.detail}. Please slow down.",
        }
    )
```

**Register in `main.py`:**
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

**Apply to routes:**
```python
# app/api/v1/routes/generation.py
from slowapi import Limiter
from app.core.rate_limit import limiter
from fastapi import Request

@router.post("/generate/instant", status_code=202)
@limiter.limit("10/minute")          # API-level: max 10 requests/minute
async def instant_generate(
    request: Request,                # Required by slowapi
    data: InstantGenerateRequest,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    ...
```

**Rate Limit Tiers:**
```
/generate/instant    → 10/minute per user (API level)
/generate/schedule   → 5/minute per user (API level)
/publish/:id         → 30/minute per user (API level)
/auth/login          → 5/minute per IP (brute force protection)
/auth/register       → 3/minute per IP
```

---

## Structured Logging (`app/utils/logger.py`)
```python
import structlog
import logging
import sys

def configure_logging(log_level: str = "INFO", json_logs: bool = True):
    """
    Production: json_logs=True → machine-readable JSON for log aggregators.
    Development: json_logs=False → human-readable colored console output.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]

    if json_logs:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger("ai_career_platform")
```

**Log Event Taxonomy** — use these exact event names for consistency:

| Event | When | Key Fields |
|-------|------|-----------|
| `generation.started` | Pipeline begins | `job_id`, `user_id`, `mode` |
| `generation.completed` | Pipeline done | `job_id`, `duration_ms`, `angle` |
| `generation.failed` | Pipeline error | `job_id`, `error` |
| `publish.started` | Publishing begins | `post_id`, `platform` |
| `publish.success` | Published | `post_id`, `platform_post_id` |
| `publish.failed` | Publish error | `post_id`, `error`, `retry_count` |
| `scheduler.job_fired` | APScheduler fires | `post_id`, `scheduled_time` |
| `scheduler.job_missed` | Misfire | `post_id`, `trigger_time` |
| `scheduler.recovery` | Startup recovery | `recovered_count` |
| `auth.login` | Successful login | `user_id` |
| `auth.register` | New user | `user_id`, `email` |
| `linkedin.token_expired` | Token check fails | `user_id` |
| `rate_limit.exceeded` | User blocked | `user_id`, `route` |

**Usage throughout codebase:**
```python
from app.utils.logger import logger

# In generation_service.py
logger.info("generation.started", job_id=job_id, user_id=user_id, mode="instant")

# In publish_service.py
logger.info("publish.success", post_id=post_id, platform="linkedin", platform_post_id=pid)
logger.error("publish.failed", post_id=post_id, error=str(e), retry_count=retry_count)

# In scheduler/tasks.py
logger.info("scheduler.job_fired", post_id=post_id, scheduled_time=str(scheduled_time))
```

---

## Request Logging Middleware (`app/middleware/logging_middleware.py`)
```python
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)

        # Log all non-health requests
        if request.url.path not in ["/health", "/"]:
            logger.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        return response
```

**Register in `main.py`:**
```python
from app.middleware.logging_middleware import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)
```

---

## AI Timeout Guard (`app/core/timeout.py`)
```python
import asyncio
from app.core.exceptions import AppException

async def with_timeout(coro, timeout_seconds: int = 30, error_code: str = "AI_TIMEOUT"):
    """
    Wraps any coroutine with a timeout.
    Raises AppException with structured error on timeout.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise AppException(
            code=error_code,
            message="Generation took too long. Please try a shorter project description.",
            status_code=408
        )
```

**Apply in AI pipeline:**
```python
# app/ai/pipeline/orchestrator.py
from app.core.timeout import with_timeout

async def run(self, project, tone, target_audience, preferred_angle):
    # Wrap entire pipeline with 90s timeout
    return await with_timeout(
        self._run_pipeline(project, tone, target_audience, preferred_angle),
        timeout_seconds=90,
        error_code="AI_TIMEOUT"
    )
```

**Apply per AI call:**
```python
# app/ai/client/gemini.py
async def generate(self, prompt, max_tokens=1024, temperature=0.7, system_prompt=None):
    async with httpx.AsyncClient(timeout=30.0) as client:  # httpx-level timeout
        ...
```

---

## LinkedIn Token Expiry Pre-Check

Add to `IntegrationService.get_decrypted_linkedin_token()` (already in Phase 06).

Add proactive logging:
```python
# Before decrypting token:
expires_at = linkedin.get("token_expires_at")
if expires_at:
    days_remaining = (expires_at - datetime.now(timezone.utc)).days
    if days_remaining < 7:
        logger.warning(
            "linkedin.token_expiring_soon",
            user_id=user_id,
            days_remaining=days_remaining
        )
    if days_remaining <= 0:
        logger.error("linkedin.token_expired", user_id=user_id)
        raise AppException("LINKEDIN_TOKEN_EXPIRED", "LinkedIn token expired. Please reconnect.", 401)
```

---

## APScheduler Misfire Listener
```python
# app/scheduler/setup.py — add listener
from apscheduler.events import EVENT_JOB_MISSED, EVENT_JOB_ERROR
from app.utils.logger import logger

def job_listener(event):
    if event.exception:
        logger.error("scheduler.job_error", job_id=event.job_id, error=str(event.exception))
    else:
        logger.warning("scheduler.job_missed", job_id=event.job_id)

scheduler.add_listener(job_listener, EVENT_JOB_MISSED | EVENT_JOB_ERROR)
```

---

## Extended Health Check (`app/api/v1/routes/health.py`)
```python
from fastapi import APIRouter
from app.core.database import db_instance
from app.scheduler.setup import scheduler
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    # DB ping
    db_ok = False
    try:
        await db_instance.client.admin.command('ping')
        db_ok = True
    except Exception:
        pass

    # Scheduler status
    scheduler_ok = scheduler.running
    pending_jobs = len(scheduler.get_jobs())

    status = "ok" if db_ok and scheduler_ok else "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "ok" if db_ok else "error",
            "scheduler": "ok" if scheduler_ok else "stopped",
        },
        "scheduler": {
            "running": scheduler_ok,
            "pending_jobs": pending_jobs
        }
    }
```

---

## Input Sanitization

Add to all text inputs at the service layer:
```python
# app/services/project_service.py
def _sanitize(self, text: str) -> str:
    """Strip leading/trailing whitespace and normalize internal spaces."""
    import re
    return re.sub(r'\s+', ' ', text.strip()) if text else text

# Apply to title, problem_solved, etc. before storing
doc = {
    "title": self._sanitize(data.title),
    "problem_solved": self._sanitize(data.problem_solved),
    ...
}
```

---

## Environment Variables

```env
# Add to backend .env
LOG_LEVEL=INFO
JSON_LOGS=true    # false for local development
```

**Update `config.py`:**
```python
LOG_LEVEL: str = "INFO"
JSON_LOGS: bool = True
```

**Call configure_logging in `main.py` lifespan:**
```python
from app.utils.logger import configure_logging
configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
```

---

## Implementation Steps (Exact Order)

1. Create `app/core/rate_limit.py` + register limiter in `main.py`
2. Apply `@limiter.limit()` decorator to all generation + auth routes
3. Update `app/utils/logger.py` with `configure_logging()`
4. Create `app/middleware/logging_middleware.py` + register in `main.py`
5. Create `app/core/timeout.py` + wrap AI pipeline
6. Add httpx `timeout=30.0` to all AI client HTTP calls
7. Add APScheduler misfire listener to `scheduler/setup.py`
8. Add token expiry pre-check logging to `integration_service.py`
9. Update `/health` endpoint with scheduler + DB status
10. Add input sanitization to all service text fields
11. Add `LOG_LEVEL`, `JSON_LOGS` to `.env` and `config.py`
12. Test: 10+ rapid requests to `/generate/instant` → 429 on 11th
13. Test: brute-force `/auth/login` → 429 after 5 attempts
14. Test: `/health` → returns scheduler running + DB ok
15. Test: JSON logs appear on console with correct fields
16. Commit: `git commit -m "Phase 12: Rate limiting, structured logging, reliability"`

---

## Testing Strategy
```python
@pytest.mark.asyncio
async def test_rate_limit_login_brute_force():
    # Send 6 POST /auth/login requests rapidly from same IP
    # 6th should return 429 with code=API_RATE_LIMIT

@pytest.mark.asyncio
async def test_ai_timeout_returns_structured_error():
    # Mock AI pipeline to sleep > 90s
    # POST /generate/instant → 408, code=AI_TIMEOUT

def test_sanitize_strips_whitespace():
    svc = ProjectService()
    assert svc._sanitize("  hello   world  ") == "hello world"

@pytest.mark.asyncio
async def test_health_check_db_down():
    # Simulate DB disconnection
    # GET /health → status=degraded, database=error
```

---

## Edge Cases
- Rate limit key function returns IP for unauthenticated, user_id for authenticated — test both
- slowapi `@limiter.limit()` requires `request: Request` as first parameter — enforce on all decorated routes
- `asyncio.TimeoutError` from `wait_for` must be caught — not `TimeoutError` from httpx (different exception)
- JSON logs in production must NOT include Python tracebacks in `message` field — use `structlog.processors.dict_tracebacks` to put them in separate field

---

## Deliverables / Checklist

- [ ] `slowapi` limiter registered in `main.py`
- [ ] `@limiter.limit("10/minute")` on `/generate/instant`
- [ ] `@limiter.limit("5/minute")` on `/auth/login`
- [ ] 429 returns `{ code: "API_RATE_LIMIT", message: "..." }`
- [ ] `structlog` configured for JSON output in production
- [ ] `RequestLoggingMiddleware` logs all requests with status + duration
- [ ] All key events use defined event names from taxonomy
- [ ] `with_timeout(90s)` wraps AI pipeline
- [ ] httpx 30s timeout on all AI client calls
- [ ] APScheduler misfire → logged as `scheduler.job_missed`
- [ ] LinkedIn token < 7 days → logged as `linkedin.token_expiring_soon`
- [ ] `/health` returns scheduler + DB status
- [ ] Input sanitization on all text fields
- [ ] `LOG_LEVEL` + `JSON_LOGS` configurable via env vars

---

## Definition of Completion
Rapid-fire requests are blocked by rate limiting with a proper error code. All key system events (generation, publish, schedule, auth) appear in structured JSON logs. AI pipeline has a 90-second hard timeout. `/health` accurately reflects system state. No unhandled 500 errors ever expose stack traces to clients.