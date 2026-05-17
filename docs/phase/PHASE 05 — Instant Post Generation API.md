# PHASE 05 — Instant Post Generation API

## Phase Goal
Expose the AI pipeline from Phase 04 as a production-ready API endpoint. Users submit a project ID, the system runs the full AI pipeline, stores results as a `post` document and a `generation_job` document, and returns the generated content. Includes rate limiting, generation job tracking, and frontend generation UI.

---

## Features Implemented
- `POST /generate/instant` — Triggers instant post generation
- `GET /generate/jobs/:id` — Polls generation job status
- Rate limiting: 5 generations/day (free), unlimited (premium)
- Generation job lifecycle tracking (`processing → completed / failed`)
- Post stored with status `generated`
- Frontend: Generation loading screen with progress steps
- Frontend: Output display with copy/edit/regenerate

---

## Technical Architecture

```
app/
├── api/v1/routes/
│   └── generation.py           ← /generate/instant, /generate/jobs/:id
├── services/
│   └── generation_service.py   ← Business logic: validate, run pipeline, save
├── repositories/
│   ├── generation_job_repository.py  ← (Phase 01)
│   └── post_repository.py           ← (Phase 01)
├── ai/
│   └── pipeline/
│       └── orchestrator.py          ← (Phase 04)
└── core/
    └── rate_limiter.py              ← Per-user daily limit check
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/generate/instant` | ✅ | Trigger instant post generation |
| GET | `/api/v1/generate/jobs/:job_id` | ✅ | Poll generation job status |
| GET | `/api/v1/posts` | ✅ | List generated posts (workspace) |
| GET | `/api/v1/posts/:id` | ✅ | Get single generated post |
| DELETE | `/api/v1/posts/:id` | ✅ | Soft delete a post |

---

## Request / Response Shapes

### POST `/generate/instant`
**Request:**
```json
{
  "project_id": "667abc...",
  "tone": "professional",
  "target_audience": "recruiters",
  "preferred_angle": null,
  "platform": "linkedin"
}
```
**Response 202 (Accepted — async processing starts):**
```json
{
  "job_id": "667xyz...",
  "status": "processing",
  "message": "Generation started. Poll /generate/jobs/667xyz... for status.",
  "estimated_seconds": 15
}
```

### GET `/generate/jobs/:job_id`
**Response 200 (processing):**
```json
{
  "job_id": "667xyz...",
  "status": "processing",
  "started_at": "2025-01-01T10:00:00"
}
```
**Response 200 (completed):**
```json
{
  "job_id": "667xyz...",
  "status": "completed",
  "generated_post_ids": ["667post1..."],
  "duration_ms": 8420,
  "posts": [
    {
      "id": "667post1...",
      "content": "I spent 3 months building something...",
      "platform": "linkedin",
      "status": "generated",
      "angle": "problem_solution",
      "tone": "professional",
      "prompt_version": "v1.2"
    }
  ]
}
```
**Response 200 (failed):**
```json
{
  "job_id": "667xyz...",
  "status": "failed",
  "error": "AI_TIMEOUT",
  "message": "Generation took too long. Please try again."
}
```

---

## Rate Limiter (`app/core/rate_limiter.py`)
```python
from datetime import datetime, timezone, timedelta
from app.repositories.user_repository import UserRepository
from app.core.exceptions import AppException

FREE_DAILY_LIMIT = 5

class GenerationRateLimiter:
    def __init__(self):
        self.user_repo = UserRepository()

    async def check_and_increment(self, user: dict) -> None:
        """
        Raises AppException if user has exceeded daily limit.
        Resets counter if it's a new day.
        """
        if user.get("plan") == "premium":
            return  # Unlimited for premium

        now = datetime.now(timezone.utc)
        reset_at = user.get("daily_generation_reset_at")

        # Check if reset needed (new day)
        if reset_at:
            if isinstance(reset_at, str):
                from dateutil.parser import parse
                reset_at = parse(reset_at)
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)
            
            if now - reset_at > timedelta(hours=24):
                await self.user_repo.reset_daily_count(user["id"])
                return  # Count just reset, proceed

        count = user.get("daily_generation_count", 0)
        if count >= FREE_DAILY_LIMIT:
            raise AppException(
                code="RATE_LIMIT_EXCEEDED",
                message=f"Free plan allows {FREE_DAILY_LIMIT} generations per day. Upgrade to premium for unlimited.",
                status_code=429
            )

        await self.user_repo.increment_daily_count(user["id"])
```

---

## Generation Service (`app/services/generation_service.py`)
```python
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.ai.pipeline.orchestrator import ContentGenerationPipeline
from app.core.rate_limiter import GenerationRateLimiter
from app.core.exceptions import AppException
from app.ai.prompts.version import PROMPT_VERSION
from app.utils.logger import logger

class GenerationService:
    def __init__(self):
        self.job_repo = GenerationJobRepository()
        self.post_repo = PostRepository()
        self.project_repo = ProjectRepository()
        self.user_repo = UserRepository()
        self.pipeline = ContentGenerationPipeline()
        self.rate_limiter = GenerationRateLimiter()

    async def start_instant_generation(
        self,
        user: dict,
        project_id: str,
        tone: str,
        target_audience: str,
        preferred_angle: str,
        platform: str
    ) -> dict:
        # 1. Rate limit check
        await self.rate_limiter.check_and_increment(user)

        # 2. Verify project ownership
        project = await self.project_repo.find_by_id(project_id)
        if not project:
            raise AppException("PROJECT_NOT_FOUND", "Project not found.", 404)
        if project["user_id"] != user["id"]:
            raise AppException("FORBIDDEN", "You do not have access to this project.", 403)

        # 3. Create generation job record
        now = datetime.now(timezone.utc)
        job_doc = {
            "user_id": ObjectId(user["id"]),
            "project_id": ObjectId(project_id),
            "status": "processing",
            "mode": "instant",
            "input_payload": {
                "tone": tone,
                "target_audience": target_audience,
                "preferred_angle": preferred_angle,
                "platform": platform
            },
            "generated_post_ids": [],
            "started_at": now,
            "completed_at": None,
            "duration_ms": None,
            "error": None,
            "prompt_version": PROMPT_VERSION
        }
        job_id = await self.job_repo.insert_one(job_doc)

        # 4. Kick off async generation (fire and forget)
        asyncio.create_task(
            self._run_pipeline(job_id, project, user["id"], tone, target_audience, preferred_angle, platform)
        )

        return {
            "job_id": job_id,
            "status": "processing",
            "message": f"Generation started. Poll /generate/jobs/{job_id} for status.",
            "estimated_seconds": 15
        }

    async def _run_pipeline(
        self,
        job_id: str,
        project: dict,
        user_id: str,
        tone: str,
        target_audience: str,
        preferred_angle: str,
        platform: str
    ):
        """Background task: runs AI pipeline and saves results."""
        try:
            result = await self.pipeline.run(
                project=project,
                tone=tone,
                target_audience=target_audience,
                preferred_angle=preferred_angle
            )

            # Save generated post
            now = datetime.now(timezone.utc)
            post_doc = {
                "user_id": ObjectId(user_id),
                "project_id": ObjectId(project["id"]),
                "generation_job_id": ObjectId(job_id),
                "content": result["content"],
                "platform": platform,
                "status": "generated",
                "mode": "instant",
                "angle": result["angle"],
                "tone": tone,
                "prompt_version": result["prompt_version"],
                "scheduled_time": None,
                "posted_at": None,
                "platform_post_ids": {},
                "retry_count": 0,
                "max_retries": 3,
                "next_retry_at": None,
                "error_log": [],
                "deleted": False,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now
            }
            post_id = await self.post_repo.insert_one(post_doc)

            # Mark job completed
            await self.job_repo.mark_completed(
                job_id, [post_id], result["duration_ms"]
            )
            logger.info("Generation job completed", job_id=job_id, post_id=post_id)

        except Exception as e:
            logger.error("Generation job failed", job_id=job_id, error=str(e))
            await self.job_repo.mark_failed(job_id, str(e))

    async def get_job_status(self, job_id: str, user_id: str) -> dict:
        job = await self.job_repo.find_by_id(job_id)
        if not job:
            raise AppException("JOB_NOT_FOUND", "Generation job not found.", 404)
        if job["user_id"] != user_id:
            raise AppException("FORBIDDEN", "Access denied.", 403)

        response = {
            "job_id": job_id,
            "status": job["status"],
            "started_at": job.get("started_at"),
            "duration_ms": job.get("duration_ms"),
        }

        if job["status"] == "completed":
            # Fetch generated posts
            posts = []
            for post_id in job.get("generated_post_ids", []):
                post = await self.post_repo.find_by_id(str(post_id))
                if post:
                    posts.append(post)
            response["generated_post_ids"] = [str(p) for p in job.get("generated_post_ids", [])]
            response["posts"] = posts

        elif job["status"] == "failed":
            response["error"] = job.get("error")
            response["message"] = "Generation failed. Please try again."

        return response

    async def get_user_posts(self, user_id: str, skip: int, limit: int) -> dict:
        from bson import ObjectId
        posts = await self.post_repo.find_by_user(user_id, skip, limit)
        total = await self.post_repo.count({"user_id": ObjectId(user_id)})
        return {"items": posts, "total": total, "skip": skip, "limit": limit}
```

---

## Generation Router (`app/api/v1/routes/generation.py`)
```python
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.generation_service import GenerationService
from app.dependencies.auth import get_current_user

router = APIRouter(tags=["Generation"])

class InstantGenerateRequest(BaseModel):
    project_id: str
    tone: str = "professional"
    target_audience: str = "recruiters"
    preferred_angle: Optional[str] = None
    platform: str = "linkedin"

@router.post("/generate/instant", status_code=202)
async def instant_generate(
    data: InstantGenerateRequest,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    return await service.start_instant_generation(
        user=current_user,
        project_id=data.project_id,
        tone=data.tone,
        target_audience=data.target_audience,
        preferred_angle=data.preferred_angle,
        platform=data.platform
    )

@router.get("/generate/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    return await service.get_job_status(job_id, current_user["id"])

@router.get("/posts")
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    return await service.get_user_posts(current_user["id"], skip, limit)

@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    from app.repositories.post_repository import PostRepository
    from app.core.exceptions import AppException
    repo = PostRepository()
    post = await repo.find_by_id(post_id)
    if not post:
        raise AppException("POST_NOT_FOUND", "Post not found.", 404)
    if post["user_id"] != current_user["id"]:
        raise AppException("FORBIDDEN", "Access denied.", 403)
    return post

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(GenerationService)
):
    from app.repositories.post_repository import PostRepository
    from app.core.exceptions import AppException
    repo = PostRepository()
    post = await repo.find_by_id(post_id)
    if not post or post["user_id"] != current_user["id"]:
        raise AppException("POST_NOT_FOUND", "Post not found.", 404)
    await repo.soft_delete(post_id)
    return {"message": "Post deleted."}
```

---

## Frontend Tasks

### 1. Generation API calls (`src/lib/generation-api.ts`)
```typescript
import api from './api';

export const startInstantGeneration = async (data: {
  project_id: string;
  tone?: string;
  target_audience?: string;
  preferred_angle?: string;
  platform?: string;
}) => {
  const res = await api.post('/generate/instant', {
    tone: 'professional',
    target_audience: 'recruiters',
    platform: 'linkedin',
    ...data,
  });
  return res.data; // { job_id, status, estimated_seconds }
};

export const pollJobStatus = async (jobId: string) => {
  const res = await api.get(`/generate/jobs/${jobId}`);
  return res.data;
};

export const getPosts = async (skip = 0, limit = 10) => {
  const res = await api.get(`/posts?skip=${skip}&limit=${limit}`);
  return res.data;
};
```

### 2. Polling Hook (`src/hooks/useGenerationJob.ts`)
```typescript
import { useState, useEffect, useRef } from 'react';
import { pollJobStatus } from '@/lib/generation-api';

export function useGenerationJob(jobId: string | null) {
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);

    const poll = async () => {
      try {
        const data = await pollJobStatus(jobId);
        setJob(data);
        if (data.status === 'completed' || data.status === 'failed') {
          setLoading(false);
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (err) {
        setLoading(false);
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000); // poll every 2 seconds

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId]);

  return { job, loading };
}
```

### 3. Generation Loading Screen (`src/components/generation/GenerationLoader.tsx`)
```tsx
'use client';
const STEPS = [
  "Understanding your project...",
  "Extracting key achievements...",
  "Selecting content angle...",
  "Crafting your hook...",
  "Writing recruiter-friendly content...",
  "Humanizing the output...",
];

export default function GenerationLoader() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStep(s => (s < STEPS.length - 1 ? s + 1 : s));
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      <p className="text-lg font-medium text-center">{STEPS[step]}</p>
      <div className="flex gap-2">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`w-2 h-2 rounded-full transition-colors ${
              i <= step ? 'bg-primary' : 'bg-muted'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
```

### 4. Generated Post Output (`src/components/generation/PostOutput.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Copy, Check } from 'lucide-react';

export default function PostOutput({ post, onRegenerate }: {
  post: any;
  onRegenerate: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [edited, setEdited] = useState(post.content);

  const handleCopy = () => {
    navigator.clipboard.writeText(edited);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">LinkedIn Post</h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy'}
          </Button>
          <Button variant="outline" size="sm" onClick={onRegenerate}>
            Regenerate
          </Button>
        </div>
      </div>
      <Textarea
        value={edited}
        onChange={e => setEdited(e.target.value)}
        className="min-h-[300px] font-mono text-sm"
      />
      <p className="text-xs text-muted-foreground">
        Angle: {post.angle} · Prompt: {post.prompt_version}
      </p>
    </div>
  );
}
```

---

## Security Considerations
- Rate limiting checked BEFORE creating job record — prevents DB spam
- `asyncio.create_task` runs pipeline in background — HTTP request returns 202 immediately, no timeout risk
- Job ownership verified in `get_job_status` — users can only poll their own jobs
- Post ownership verified in all post endpoints

---

## Environment Variables
No new variables (uses AI keys from Phase 04).

---

## Implementation Steps (Exact Order)

1. Create `app/core/rate_limiter.py`
2. Create `app/services/generation_service.py`
3. Create `app/api/v1/routes/generation.py`
4. Register generation router in `app/api/v1/router.py`
5. Test `POST /generate/instant` via Swagger → get `job_id`
6. Test `GET /generate/jobs/:job_id` → poll until `completed`
7. Verify generated post saved in MongoDB with `status: "generated"`
8. Test rate limiting: make 6 requests → 6th returns 429
9. Create frontend `src/lib/generation-api.ts`
10. Create `useGenerationJob` polling hook
11. Create `GenerationLoader` component
12. Create `PostOutput` component
13. Wire up the full Instant Mode flow page: `ProjectForm → POST → Loading → PostOutput`
14. Test full end-to-end from browser
15. Commit: `git commit -m "Phase 05: Instant post generation API + frontend flow"`

---

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_instant_generate_rate_limit():
    # Mock user with daily_generation_count=5 (free plan)
    # POST /generate/instant → 429, code=RATE_LIMIT_EXCEEDED

@pytest.mark.asyncio
async def test_instant_generate_wrong_project():
    # POST /generate/instant with another user's project_id → 403

@pytest.mark.asyncio
async def test_job_polling_completed():
    # Create job, mock pipeline completion
    # GET /generate/jobs/:id → status=completed, posts array populated

@pytest.mark.asyncio
async def test_job_polling_failed():
    # Simulate pipeline failure → job status=failed, error field populated
```

---

## Edge Cases
- Pipeline takes > 30 seconds → LLM timeout → job marked `failed` with `AI_TIMEOUT` error
- User refreshes page during generation → frontend uses `job_id` from localStorage to resume polling
- Duplicate generation request while job is `processing` → allow (separate jobs)
- `asyncio.create_task` in test environment → use `pytest-asyncio` and proper cleanup
- Free user resets at midnight → `daily_generation_reset_at` check ensures correct reset

---

## Deliverables / Checklist

- [ ] `POST /generate/instant` → returns `job_id` with 202
- [ ] `GET /generate/jobs/:id` → returns correct status
- [ ] Generation job record created in `generation_jobs` collection
- [ ] Generated post saved in `posts` collection with status `generated`
- [ ] Rate limiting: free users blocked after 5/day
- [ ] Premium users unlimited
- [ ] `GET /posts` returns user's generated posts
- [ ] `DELETE /posts/:id` soft deletes post
- [ ] Frontend `GenerationLoader` shows step-by-step progress
- [ ] Frontend `PostOutput` shows post with copy/edit
- [ ] Polling auto-stops on `completed` or `failed`
- [ ] End-to-end: project → generate → post displayed in browser

---

## Definition of Completion
A logged-in user can select a project, click Generate, see the loading screen, and within 15-30 seconds see their LinkedIn post. The post is saved in MongoDB. Clicking Copy works. Rate limiting blocks free users after 5 attempts/day.