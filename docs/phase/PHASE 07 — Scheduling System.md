# PHASE 07 — Scheduling System (APScheduler + Growth Automation)

## Phase Goal
Implement the Growth Automation mode. Users can generate multiple posts with a posting schedule, and the system auto-publishes each post at the configured time using APScheduler. Includes scheduler recovery on server restart, retry-with-backoff on publish failure, and job persistence via MongoDB.

---

## Features Implemented
- `POST /generate/schedule` — Generate N posts with a posting schedule
- APScheduler wired into FastAPI lifespan
- Startup recovery: re-registers all `scheduled` posts on server restart
- Auto-publish task: runs at scheduled time, publishes to platform, updates post status
- Retry-with-backoff: 3 attempts (1 min → 5 min → 15 min)
- `GET /schedule` — Fetch user's upcoming scheduled posts
- `PUT /schedule/:post_id/reschedule` — Change schedule time
- `DELETE /schedule/:post_id` — Cancel a scheduled post
- Frontend: Schedule configuration UI (post count, interval, start date, time)
- Frontend: Content Calendar view

---

## Technical Architecture

```
app/
├── scheduler/
│   ├── __init__.py
│   ├── setup.py              ← APScheduler instance + startup/shutdown
│   ├── tasks.py              ← publish_scheduled_post() task function
│   └── recovery.py           ← On startup: reload scheduled jobs from DB
├── services/
│   ├── schedule_service.py   ← Business logic for scheduling
│   └── publish_service.py    ← (Phase 06) — called by scheduler task
├── api/v1/routes/
│   └── schedule.py           ← /generate/schedule, /schedule endpoints
└── repositories/
    ├── post_repository.py     ← find_scheduled_pending()
    └── scheduled_post_repository.py
```

---

## APScheduler Setup (`app/scheduler/setup.py`)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

# Singleton scheduler instance
scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    executors={"default": AsyncIOExecutor()},
    job_defaults={
        "coalesce": False,
        "max_instances": 1,
        "misfire_grace_time": 300  # 5 min grace window for missed jobs
    }
)

def get_scheduler() -> AsyncIOScheduler:
    return scheduler
```

---

## Update `app/main.py` Lifespan
```python
# app/main.py
from app.scheduler.setup import scheduler
from app.scheduler.recovery import recover_scheduled_jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Connect DB
    await connect_db()
    await create_indexes(db_instance.db)
    
    # 2. Start scheduler
    scheduler.start()
    
    # 3. Recover scheduled jobs from DB (handles server restarts)
    await recover_scheduled_jobs()
    
    yield
    
    # Shutdown
    scheduler.shutdown(wait=False)
    await close_db()
```

---

## Scheduler Recovery (`app/scheduler/recovery.py`)
```python
from app.repositories.post_repository import PostRepository
from app.scheduler.tasks import publish_scheduled_post
from app.scheduler.setup import scheduler
from app.utils.logger import logger
from datetime import datetime, timezone

async def recover_scheduled_jobs():
    """
    Called on FastAPI startup.
    Finds all posts with status='scheduled' in DB and re-registers them
    into APScheduler. This handles server restarts gracefully.
    
    CRITICAL: Without this, a server restart loses all in-memory APScheduler jobs.
    """
    post_repo = PostRepository()
    pending_posts = await post_repo.find_scheduled_pending()
    
    recovered = 0
    skipped = 0
    
    for post in pending_posts:
        scheduled_time = post.get("scheduled_time")
        if not scheduled_time:
            continue
        
        # Parse datetime
        if isinstance(scheduled_time, str):
            from dateutil.parser import parse
            scheduled_time = parse(scheduled_time)
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        
        # If scheduled time is in the past (missed while server was down)
        if scheduled_time < now:
            # Publish immediately (within misfire grace)
            scheduler.add_job(
                publish_scheduled_post,
                trigger="date",
                run_date=now,
                args=[post["id"]],
                id=f"post_{post['id']}",
                replace_existing=True
            )
            logger.warning("Recovering missed scheduled post — publishing immediately", 
                          post_id=post["id"])
        else:
            scheduler.add_job(
                publish_scheduled_post,
                trigger="date",
                run_date=scheduled_time,
                args=[post["id"]],
                id=f"post_{post['id']}",
                replace_existing=True
            )
            recovered += 1
    
    logger.info("Scheduler recovery complete", 
                recovered=recovered, 
                immediate=len(pending_posts) - recovered - skipped)
```

---

## Scheduler Task (`app/scheduler/tasks.py`)
```python
from datetime import datetime, timezone, timedelta
from app.repositories.post_repository import PostRepository
from app.services.publish_service import PublishService
from app.scheduler.setup import scheduler
from app.utils.logger import logger

# Retry backoff intervals in minutes
RETRY_BACKOFF = [1, 5, 15]

async def publish_scheduled_post(post_id: str):
    """
    APScheduler calls this at the scheduled time.
    Publishes the post to its configured platform.
    On failure: retries with backoff up to max_retries.
    """
    post_repo = PostRepository()
    publish_service = PublishService()
    
    post = await post_repo.find_by_id(post_id)
    if not post:
        logger.error("Scheduled post not found", post_id=post_id)
        return
    
    # Skip if already posted or deleted
    if post["status"] in ("posted", "failed") or post.get("deleted"):
        logger.info("Skipping post — already processed", post_id=post_id, status=post["status"])
        return

    logger.info("Executing scheduled post", post_id=post_id, platform=post.get("platform"))

    try:
        await publish_service.publish_post(post["user_id"], post_id)
        logger.info("Scheduled post published successfully", post_id=post_id)

    except Exception as e:
        retry_count = post.get("retry_count", 0)
        max_retries = post.get("max_retries", 3)
        
        logger.error("Scheduled post publish failed", 
                    post_id=post_id, 
                    attempt=retry_count + 1,
                    error=str(e))

        if retry_count < max_retries:
            # Calculate next retry time
            backoff_minutes = RETRY_BACKOFF[min(retry_count, len(RETRY_BACKOFF) - 1)]
            next_retry = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
            
            # Update retry count in DB
            await post_repo.increment_retry(post_id, next_retry)
            
            # Re-schedule with backoff
            scheduler.add_job(
                publish_scheduled_post,
                trigger="date",
                run_date=next_retry,
                args=[post_id],
                id=f"post_{post_id}_retry_{retry_count + 1}",
                replace_existing=True
            )
            logger.info("Scheduled retry", post_id=post_id, 
                       next_retry=next_retry.isoformat(),
                       attempt=retry_count + 1)
        else:
            # Max retries exhausted — mark as permanently failed
            await post_repo.update_status(post_id, "failed", {
                "error_log": [str(e)]
            })
            logger.error("Post permanently failed after max retries", post_id=post_id)
```

---

## Schedule Service (`app/services/schedule_service.py`)
```python
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.generation_job_repository import GenerationJobRepository
from app.ai.pipeline.orchestrator import ContentGenerationPipeline
from app.core.rate_limiter import GenerationRateLimiter
from app.core.exceptions import AppException
from app.scheduler.setup import scheduler
from app.scheduler.tasks import publish_scheduled_post
from app.ai.prompts.version import PROMPT_VERSION
from app.utils.logger import logger
from typing import List
import asyncio

class ScheduleService:
    def __init__(self):
        self.post_repo = PostRepository()
        self.project_repo = ProjectRepository()
        self.job_repo = GenerationJobRepository()
        self.pipeline = ContentGenerationPipeline()
        self.rate_limiter = GenerationRateLimiter()

    async def create_schedule(
        self,
        user: dict,
        project_id: str,
        post_count: int,
        start_date: datetime,
        interval_hours: int,
        tone: str,
        target_audience: str,
        platform: str
    ) -> dict:
        """
        Generates `post_count` posts and schedules them at `interval_hours` apart
        starting from `start_date`.
        """
        # Validate post count
        if post_count < 1 or post_count > 20:
            raise AppException("INVALID_POST_COUNT", 
                             "Post count must be between 1 and 20.", 400)

        # Verify project ownership
        project = await self.project_repo.find_by_id(project_id)
        if not project:
            raise AppException("PROJECT_NOT_FOUND", "Project not found.", 404)
        if project["user_id"] != user["id"]:
            raise AppException("FORBIDDEN", "Access denied.", 403)

        # Create generation job
        now = datetime.now(timezone.utc)
        job_doc = {
            "user_id": ObjectId(user["id"]),
            "project_id": ObjectId(project_id),
            "status": "processing",
            "mode": "schedule",
            "input_payload": {
                "post_count": post_count,
                "interval_hours": interval_hours,
                "start_date": start_date.isoformat(),
                "tone": tone,
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

        # Fire background generation
        asyncio.create_task(
            self._generate_and_schedule(
                job_id, project, user["id"],
                post_count, start_date, interval_hours,
                tone, target_audience, platform
            )
        )

        return {
            "job_id": job_id,
            "status": "processing",
            "message": f"Generating {post_count} posts. Poll /generate/jobs/{job_id} for status.",
            "post_count": post_count,
            "estimated_seconds": post_count * 20
        }

    async def _generate_and_schedule(
        self,
        job_id: str,
        project: dict,
        user_id: str,
        post_count: int,
        start_date: datetime,
        interval_hours: int,
        tone: str,
        target_audience: str,
        platform: str
    ):
        """Background task: generates all posts and schedules each one."""
        import time
        start_time = time.time()
        post_ids = []

        try:
            # Use varied angles across the series
            from app.ai.constants import CONTENT_ANGLES
            angles = CONTENT_ANGLES[:post_count]  # cycle if fewer angles than posts

            for i in range(post_count):
                scheduled_time = start_date + timedelta(hours=interval_hours * i)
                angle = angles[i % len(angles)]

                # Generate post with different angle each time
                result = await self.pipeline.run(
                    project=project,
                    tone=tone,
                    target_audience=target_audience,
                    preferred_angle=angle
                )

                # Save post with scheduled status
                now = datetime.now(timezone.utc)
                post_doc = {
                    "user_id": ObjectId(user_id),
                    "project_id": ObjectId(project["id"]),
                    "generation_job_id": ObjectId(job_id),
                    "content": result["content"],
                    "platform": platform,
                    "status": "scheduled",
                    "mode": "schedule",
                    "angle": result["angle"],
                    "tone": tone,
                    "prompt_version": result["prompt_version"],
                    "scheduled_time": scheduled_time,
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
                post_ids.append(post_id)

                # Register in APScheduler
                scheduler.add_job(
                    publish_scheduled_post,
                    trigger="date",
                    run_date=scheduled_time,
                    args=[post_id],
                    id=f"post_{post_id}",
                    replace_existing=True
                )
                logger.info("Post scheduled", post_id=post_id, run_at=scheduled_time.isoformat())

            duration_ms = int((time.time() - start_time) * 1000)
            await self.job_repo.mark_completed(job_id, post_ids, duration_ms)
            logger.info("Schedule generation complete", job_id=job_id, count=post_count)

        except Exception as e:
            logger.error("Schedule generation failed", job_id=job_id, error=str(e))
            await self.job_repo.mark_failed(job_id, str(e))

    async def get_user_schedule(self, user_id: str, skip: int = 0, limit: int = 20) -> dict:
        from bson import ObjectId
        posts = await self.post_repo.find_many(
            {"user_id": ObjectId(user_id), "status": "scheduled"},
            skip=skip, limit=limit
        )
        total = await self.post_repo.count(
            {"user_id": ObjectId(user_id), "status": "scheduled"}
        )
        # Sort by scheduled_time
        posts.sort(key=lambda p: p.get("scheduled_time") or "")
        return {"items": posts, "total": total, "skip": skip, "limit": limit}

    async def reschedule_post(self, post_id: str, user_id: str, new_time: datetime) -> dict:
        post = await self.post_repo.find_by_id(post_id)
        if not post or post["user_id"] != user_id:
            raise AppException("POST_NOT_FOUND", "Post not found.", 404)
        if post["status"] == "posted":
            raise AppException("ALREADY_POSTED", "Cannot reschedule a posted post.", 400)

        # Update DB
        await self.post_repo.update_one(post_id, {
            "scheduled_time": new_time,
            "status": "scheduled"
        })

        # Update APScheduler job
        job_id = f"post_{post_id}"
        if scheduler.get_job(job_id):
            scheduler.reschedule_job(job_id, trigger="date", run_date=new_time)
        else:
            # Re-register if missing
            scheduler.add_job(
                publish_scheduled_post,
                trigger="date",
                run_date=new_time,
                args=[post_id],
                id=job_id,
                replace_existing=True
            )

        return {"message": "Post rescheduled.", "new_time": new_time.isoformat()}

    async def cancel_scheduled_post(self, post_id: str, user_id: str) -> None:
        post = await self.post_repo.find_by_id(post_id)
        if not post or post["user_id"] != user_id:
            raise AppException("POST_NOT_FOUND", "Post not found.", 404)
        if post["status"] == "posted":
            raise AppException("ALREADY_POSTED", "Cannot cancel a posted post.", 400)

        # Remove from APScheduler
        job_id = f"post_{post_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        # Soft delete from DB
        await self.post_repo.soft_delete(post_id)
```

---

## Schedule Router (`app/api/v1/routes/schedule.py`)
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.services.schedule_service import ScheduleService
from app.dependencies.auth import get_current_user

router = APIRouter(tags=["Scheduling"])

class CreateScheduleRequest(BaseModel):
    project_id: str
    post_count: int = 5
    start_date: datetime
    interval_hours: int = 48      # default: every 2 days
    tone: str = "professional"
    target_audience: str = "recruiters"
    platform: str = "linkedin"

class RescheduleRequest(BaseModel):
    new_time: datetime

@router.post("/generate/schedule", status_code=202)
async def create_schedule(
    data: CreateScheduleRequest,
    current_user: dict = Depends(get_current_user),
    service: ScheduleService = Depends(ScheduleService)
):
    return await service.create_schedule(
        user=current_user,
        project_id=data.project_id,
        post_count=data.post_count,
        start_date=data.start_date,
        interval_hours=data.interval_hours,
        tone=data.tone,
        target_audience=data.target_audience,
        platform=data.platform
    )

@router.get("/schedule")
async def get_schedule(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    service: ScheduleService = Depends(ScheduleService)
):
    return await service.get_user_schedule(current_user["id"], skip, limit)

@router.put("/schedule/{post_id}/reschedule")
async def reschedule(
    post_id: str,
    data: RescheduleRequest,
    current_user: dict = Depends(get_current_user),
    service: ScheduleService = Depends(ScheduleService)
):
    return await service.reschedule_post(post_id, current_user["id"], data.new_time)

@router.delete("/schedule/{post_id}")
async def cancel_scheduled(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    service: ScheduleService = Depends(ScheduleService)
):
    await service.cancel_scheduled_post(post_id, current_user["id"])
    return {"message": "Scheduled post cancelled."}
```

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/generate/schedule` | ✅ | Generate + schedule N posts |
| GET | `/api/v1/schedule` | ✅ | Get user's scheduled posts |
| PUT | `/api/v1/schedule/:id/reschedule` | ✅ | Change post's scheduled time |
| DELETE | `/api/v1/schedule/:id` | ✅ | Cancel scheduled post |

---

## Frontend Tasks

### 1. Schedule Config Form (`src/components/schedule/ScheduleConfigForm.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Props { projectId: string; onScheduled: (jobId: string) => void; }

export default function ScheduleConfigForm({ projectId, onScheduled }: Props) {
  const [form, setForm] = useState({
    post_count: 5,
    interval_hours: 48,
    start_date: '',
    tone: 'professional',
    target_audience: 'recruiters',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await api.post('/generate/schedule', {
        project_id: projectId,
        ...form,
        start_date: new Date(form.start_date).toISOString(),
      });
      onScheduled(res.data.job_id);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-md">
      <div>
        <Label>Number of Posts</Label>
        <Select onValueChange={v => setForm(p => ({ ...p, post_count: +v }))}>
          <SelectTrigger><SelectValue placeholder="5 posts" /></SelectTrigger>
          <SelectContent>
            {[3, 5, 7, 10].map(n => (
              <SelectItem key={n} value={String(n)}>{n} posts</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>Posting Frequency</Label>
        <Select onValueChange={v => setForm(p => ({ ...p, interval_hours: +v }))}>
          <SelectTrigger><SelectValue placeholder="Every 2 days" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="24">Daily</SelectItem>
            <SelectItem value="48">Every 2 days</SelectItem>
            <SelectItem value="72">Every 3 days</SelectItem>
            <SelectItem value="168">Weekly</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>Start Date & Time</Label>
        <Input
          type="datetime-local"
          value={form.start_date}
          onChange={e => setForm(p => ({ ...p, start_date: e.target.value }))}
        />
      </div>
      <Button onClick={handleSubmit} disabled={loading} className="w-full">
        {loading ? 'Generating schedule...' : 'Build Content Schedule'}
      </Button>
    </div>
  );
}
```

### 2. Content Calendar (`src/components/schedule/ContentCalendar.tsx`)
```tsx
'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Badge } from '@/components/ui/badge';

export default function ContentCalendar() {
  const [posts, setPosts] = useState<any[]>([]);

  useEffect(() => {
    api.get('/schedule').then(res => setPosts(res.data.items));
  }, []);

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-lg">Upcoming Posts</h3>
      {posts.length === 0 && (
        <p className="text-muted-foreground text-sm">No scheduled posts yet.</p>
      )}
      {posts.map(post => (
        <div key={post.id} className="border rounded-lg p-4 flex justify-between items-start">
          <div>
            <p className="text-sm text-muted-foreground">
              {new Date(post.scheduled_time).toLocaleString()}
            </p>
            <p className="mt-1 text-sm line-clamp-2">{post.content}</p>
          </div>
          <Badge variant={post.status === 'scheduled' ? 'default' : 'secondary'}>
            {post.status}
          </Badge>
        </div>
      ))}
    </div>
  );
}
```

---

## Security Considerations
- APScheduler jobs run with `user_id` embedded in task args — publish_service re-verifies ownership
- `misfire_grace_time = 300s` — prevents lost jobs during brief server restarts
- Scheduler runs in-process → horizontal scaling requires Redis job store (document as known limitation)
- `max_instances = 1` per job — prevents duplicate publish of same post

---

## Environment Variables
```env
# No new variables needed
# APScheduler runs in-memory — no Redis URL required for MVP
```

---

## Third-Party Services Required
| Package | Purpose |
|---------|---------|
| `apscheduler==3.10.4` | Already in requirements.txt |

---

## Implementation Steps (Exact Order)

1. Create `app/scheduler/setup.py` — APScheduler singleton
2. Create `app/scheduler/tasks.py` — `publish_scheduled_post` function
3. Create `app/scheduler/recovery.py` — `recover_scheduled_jobs`
4. Update `app/main.py` lifespan to start scheduler + call recovery
5. Create `app/services/schedule_service.py`
6. Create `app/api/v1/routes/schedule.py`
7. Register schedule router in `api_router`
8. Test: create a schedule with `start_date` 2 minutes in the future → wait → verify post is published
9. Test restart recovery: schedule a post, restart server, verify APScheduler re-registers it
10. Test retry: mock LinkedIn to fail → verify retry is scheduled with backoff
11. Create frontend `ScheduleConfigForm`
12. Create frontend `ContentCalendar`
13. Wire Growth Automation mode page: select mode → Project form → Schedule config → Calendar view
14. Commit: `git commit -m "Phase 07: Scheduling system with APScheduler"`

---

## Testing Strategy
```python
@pytest.mark.asyncio
async def test_scheduler_recovery_re_registers_pending_posts():
    # Mock PostRepository.find_scheduled_pending → return 2 posts with future times
    # Call recover_scheduled_jobs()
    # Assert scheduler has 2 jobs registered

@pytest.mark.asyncio
async def test_retry_backoff_schedules_next_attempt():
    # Mock publish_service to raise exception
    # Call publish_scheduled_post(post_id)
    # Assert retry_count incremented + new APScheduler job created with 1-min delay

@pytest.mark.asyncio
async def test_max_retries_marks_failed():
    # Mock post with retry_count=3, max_retries=3
    # Call publish_scheduled_post
    # Assert post.status == "failed"
```

---

## Edge Cases
- Server restarts → `recover_scheduled_jobs` on lifespan startup handles it
- Scheduled time in the past on recovery → publish immediately
- LinkedIn token expired at publish time → retry with `LINKEDIN_TOKEN_EXPIRED` error, eventually mark `failed`
- User cancels post after it's already `publishing` → check status before cancellation
- Two APScheduler instances (if ever scaled horizontally) → duplicate publish risk; document as Redis/Celery migration requirement

---

## Deliverables / Checklist

- [ ] APScheduler starts on FastAPI lifespan startup
- [ ] `recover_scheduled_jobs` called on startup and re-registers pending posts
- [ ] `POST /generate/schedule` generates N posts and schedules them
- [ ] Each post has correct `scheduled_time` spaced by `interval_hours`
- [ ] APScheduler fires `publish_scheduled_post` at correct time
- [ ] Published post: `status = "posted"`, `posted_at` set, `platform_post_ids` populated
- [ ] Failed publish: retried with 1min → 5min → 15min backoff
- [ ] After 3 failures: `status = "failed"`
- [ ] `GET /schedule` returns upcoming posts sorted by time
- [ ] `PUT /schedule/:id/reschedule` updates both DB and APScheduler
- [ ] `DELETE /schedule/:id` cancels APScheduler job and soft-deletes
- [ ] Server restart recovery tested and verified
- [ ] Frontend calendar shows scheduled posts
- [ ] All scheduler tests pass

---

## Definition of Completion
User can choose Growth Automation, configure 5 posts at 2-day intervals starting tomorrow, and all 5 posts get published automatically at their scheduled times. A server restart doesn't lose any scheduled jobs. Failed publishes retry with backoff and eventually mark as failed after 3 attempts.