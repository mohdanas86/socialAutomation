# PHASE 01 — Database Design & MongoDB Schema

## Phase Goal
Define and implement ALL MongoDB collections, indexes, and repository (data access) layer for the entire platform. Every future phase pulls from this schema. Get it right before writing any feature logic.

---

## Features Implemented
- All 5 core MongoDB collections defined with full schemas
- Motor async repository pattern (no raw DB calls in services)
- MongoDB indexes created on startup (for query performance)
- Soft delete pattern implemented across all collections
- Base repository class with reusable CRUD operations
- ObjectId ↔ string conversion utilities

---

## Technical Architecture

```
app/
├── repositories/
│   ├── __init__.py
│   ├── base.py              ← BaseRepository (generic CRUD)
│   ├── user_repository.py
│   ├── project_repository.py
│   ├── post_repository.py
│   ├── generation_job_repository.py
│   └── scheduled_post_repository.py
├── models/
│   ├── __init__.py
│   ├── user.py              ← Pydantic schemas for User
│   ├── project.py
│   ├── post.py
│   └── generation_job.py
└── core/
    └── database.py          ← Add index creation here
```

---

## Collections & Full Schema

### Collection: `users`
```json
{
  "_id": "ObjectId",
  "name": "Anas Khan",
  "email": "anas@srm.edu",
  "hashed_password": "$2b$12$...",
  "is_verified": false,
  "is_active": true,
  "plan": "free",
  "daily_generation_count": 0,
  "daily_generation_reset_at": "ISODate()",
  "features": {
    "scheduler_enabled": true
  },
  "integrations": {
    "linkedin": {
      "linkedin_id": "urn:li:person:123",
      "access_token": "AQV...",
      "refresh_token": null,
      "token_expires_at": "ISODate()",
      "connected": false,
      "connected_at": null
    }
  },
  "created_at": "ISODate()",
  "updated_at": "ISODate()",
  "deleted": false,
  "deleted_at": null
}
```

### Collection: `projects`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "AgriLenses",
  "github_url": "https://github.com/user/agrilenses",
  "readme_context": "Raw README text (truncated to 4000 chars)",
  "problem_solved": "Farmers cannot detect crop diseases early",
  "tech_stack": ["Python", "TensorFlow", "FastAPI", "React"],
  "features": ["Disease detection", "92% accuracy"],
  "results_impact": "Reduced crop loss by 30% in pilot",
  "analysis_cache": {
    "problem": "Early crop disease detection",
    "value": "Saves farmer income by early detection",
    "technical_depth": "high",
    "audience_relevance": "agritech, ML engineers, recruiters",
    "angles": ["achievement", "problem-solution", "technical-breakdown"],
    "cached_at": "ISODate()"
  },
  "created_at": "ISODate()",
  "updated_at": "ISODate()",
  "deleted": false,
  "deleted_at": null
}
```

### Collection: `posts`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "project_id": "ObjectId",
  "generation_job_id": "ObjectId",
  "content": "After 3 months of late nights...",
  "platform": "linkedin",
  "status": "scheduled",
  "mode": "instant",
  "angle": "problem-solution",
  "tone": "professional",
  "prompt_version": "v1.2",
  "scheduled_time": "ISODate()",
  "posted_at": null,
  "platform_post_ids": {
    "linkedin": "urn:li:share:123"
  },
  "retry_count": 0,
  "max_retries": 3,
  "next_retry_at": null,
  "error_log": [],
  "deleted": false,
  "deleted_at": null,
  "created_at": "ISODate()",
  "updated_at": "ISODate()"
}
```

**Post Status Flow:**
```
draft → generated → scheduled → publishing → posted
                                           ↘ failed (after max_retries)
```

### Collection: `generation_jobs`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "project_id": "ObjectId",
  "status": "processing",
  "mode": "instant",
  "input_payload": {
    "title": "AgriLenses",
    "problem_solved": "...",
    "tech_stack": ["Python"],
    "tone": "professional",
    "target_audience": "recruiters"
  },
  "selected_angle": "problem-solution",
  "generated_post_ids": ["ObjectId"],
  "started_at": "ISODate()",
  "completed_at": null,
  "duration_ms": null,
  "error": null,
  "prompt_version": "v1.2"
}
```

**Generation Job Status Flow:**
```
processing → completed
           ↘ failed
```

### Collection: `scheduled_posts`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "post_id": "ObjectId",
  "apscheduler_job_id": "job_abc123",
  "platform": "linkedin",
  "scheduled_time": "ISODate()",
  "status": "pending",
  "created_at": "ISODate()",
  "executed_at": null
}
```

---

## MongoDB Indexes (created on app startup)

```python
# In app/core/database.py → create_indexes()

async def create_indexes(db):
    # users
    await db.users.create_index("email", unique=True)
    await db.users.create_index("deleted")

    # projects
    await db.projects.create_index("user_id")
    await db.projects.create_index([("user_id", 1), ("deleted", 1)])

    # posts
    await db.posts.create_index("user_id")
    await db.posts.create_index("project_id")
    await db.posts.create_index("status")
    await db.posts.create_index([("user_id", 1), ("status", 1)])
    await db.posts.create_index([("status", 1), ("scheduled_time", 1)])  # for scheduler recovery

    # generation_jobs
    await db.generation_jobs.create_index("user_id")
    await db.generation_jobs.create_index("status")

    # scheduled_posts
    await db.scheduled_posts.create_index("user_id")
    await db.scheduled_posts.create_index("post_id")
    await db.scheduled_posts.create_index("status")
```

---

## Base Repository

```python
# app/repositories/base.py
from bson import ObjectId
from typing import Optional, List, Dict, Any
from app.core.database import get_db

class BaseRepository:
    collection_name: str = ""

    @property
    def collection(self):
        return get_db()[self.collection_name]

    def _to_str_id(self, doc: dict) -> dict:
        """Convert ObjectId fields to strings for Pydantic."""
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        if doc and "user_id" in doc:
            doc["user_id"] = str(doc["user_id"])
        if doc and "project_id" in doc:
            doc["project_id"] = str(doc["project_id"])
        return doc

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one(
            {"_id": ObjectId(id), "deleted": False}
        )
        return self._to_str_id(doc) if doc else None

    async def find_one(self, filter: dict) -> Optional[dict]:
        doc = await self.collection.find_one({**filter, "deleted": False})
        return self._to_str_id(doc) if doc else None

    async def find_many(
        self, filter: dict, skip: int = 0, limit: int = 20
    ) -> List[dict]:
        cursor = self.collection.find(
            {**filter, "deleted": False}
        ).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._to_str_id(d) for d in docs]

    async def insert_one(self, data: dict) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def update_one(self, id: str, update_data: dict) -> bool:
        from datetime import datetime, timezone
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def soft_delete(self, id: str) -> bool:
        from datetime import datetime, timezone
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def count(self, filter: dict) -> int:
        return await self.collection.count_documents(
            {**filter, "deleted": False}
        )
```

---

## Repository Implementations

### User Repository
```python
# app/repositories/user_repository.py
from app.repositories.base import BaseRepository
from typing import Optional

class UserRepository(BaseRepository):
    collection_name = "users"

    async def find_by_email(self, email: str) -> Optional[dict]:
        return await self.find_one({"email": email})

    async def increment_daily_count(self, user_id: str) -> None:
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"daily_generation_count": 1}}
        )

    async def reset_daily_count(self, user_id: str) -> None:
        from bson import ObjectId
        from datetime import datetime, timezone
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "daily_generation_count": 0,
                "daily_generation_reset_at": datetime.now(timezone.utc)
            }}
        )

    async def update_linkedin_integration(
        self, user_id: str, integration_data: dict
    ) -> None:
        await self.update_one(user_id, {
            "integrations.linkedin": integration_data
        })
```

### Project Repository
```python
# app/repositories/project_repository.py
from app.repositories.base import BaseRepository
from bson import ObjectId
from typing import Optional

class ProjectRepository(BaseRepository):
    collection_name = "projects"

    async def find_by_user(self, user_id: str, skip=0, limit=20):
        return await self.find_many({"user_id": ObjectId(user_id)}, skip, limit)

    async def update_analysis_cache(self, project_id: str, cache: dict):
        from datetime import datetime, timezone
        cache["cached_at"] = datetime.now(timezone.utc)
        await self.update_one(project_id, {"analysis_cache": cache})
```

### Post Repository
```python
# app/repositories/post_repository.py
from app.repositories.base import BaseRepository
from bson import ObjectId
from typing import List

class PostRepository(BaseRepository):
    collection_name = "posts"

    async def find_by_user(self, user_id: str, skip=0, limit=20):
        return await self.find_many({"user_id": ObjectId(user_id)}, skip, limit)

    async def find_scheduled_pending(self) -> List[dict]:
        """Used on startup to re-register APScheduler jobs."""
        cursor = self.collection.find({
            "status": "scheduled",
            "deleted": False
        })
        docs = await cursor.to_list(length=500)
        return [self._to_str_id(d) for d in docs]

    async def update_status(self, post_id: str, status: str, extra: dict = None):
        data = {"status": status}
        if extra:
            data.update(extra)
        return await self.update_one(post_id, data)

    async def increment_retry(self, post_id: str, next_retry_at):
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(post_id)},
            {
                "$inc": {"retry_count": 1},
                "$set": {"next_retry_at": next_retry_at}
            }
        )
```

### Generation Job Repository
```python
# app/repositories/generation_job_repository.py
from app.repositories.base import BaseRepository
from bson import ObjectId

class GenerationJobRepository(BaseRepository):
    collection_name = "generation_jobs"

    async def mark_completed(self, job_id: str, post_ids: list, duration_ms: int):
        from datetime import datetime, timezone
        await self.update_one(job_id, {
            "status": "completed",
            "generated_post_ids": [ObjectId(pid) for pid in post_ids],
            "completed_at": datetime.now(timezone.utc),
            "duration_ms": duration_ms
        })

    async def mark_failed(self, job_id: str, error: str):
        from datetime import datetime, timezone
        await self.update_one(job_id, {
            "status": "failed",
            "error": error,
            "completed_at": datetime.now(timezone.utc)
        })
```

---

## Pydantic Models

### User Models (`app/models/user.py`)
```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LinkedInIntegration(BaseModel):
    linkedin_id: Optional[str] = None
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    connected: bool = False
    connected_at: Optional[datetime] = None

class UserIntegrations(BaseModel):
    linkedin: LinkedInIntegration = LinkedInIntegration()

class UserFeatures(BaseModel):
    scheduler_enabled: bool = True

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    plan: str
    is_active: bool
    integrations: UserIntegrations
    created_at: datetime
```

### Project Models (`app/models/project.py`)
```python
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    github_url: Optional[str] = None
    readme_context: Optional[str] = None
    problem_solved: str = Field(..., min_length=10)
    tech_stack: List[str] = Field(..., min_items=1)
    features: Optional[List[str]] = None
    results_impact: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    github_url: Optional[str]
    problem_solved: str
    tech_stack: List[str]
    created_at: datetime
```

### Post Models (`app/models/post.py`)
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PostResponse(BaseModel):
    id: str
    project_id: str
    content: str
    platform: str
    status: str
    mode: str
    angle: Optional[str]
    tone: Optional[str]
    scheduled_time: Optional[datetime]
    posted_at: Optional[datetime]
    created_at: datetime
```

---

## API Endpoints
None exposed in this phase. Repositories are the data layer — no routes yet.

---

## Backend Tasks
1. Implement `BaseRepository`
2. Implement all 5 repository classes
3. Implement all Pydantic models
4. Add `create_indexes()` call to `lifespan` startup event
5. Write repository unit tests with `mongomock`

---

## Frontend Tasks
- Define TypeScript interfaces matching all response models:

```typescript
// src/types/index.ts

export interface User {
  id: string;
  name: string;
  email: string;
  plan: 'free' | 'premium';
  integrations: {
    linkedin: {
      connected: boolean;
      connected_at?: string;
    };
  };
}

export interface Project {
  id: string;
  title: string;
  github_url?: string;
  problem_solved: string;
  tech_stack: string[];
  created_at: string;
}

export interface Post {
  id: string;
  project_id: string;
  content: string;
  platform: string;
  status: 'draft' | 'generated' | 'scheduled' | 'publishing' | 'posted' | 'failed';
  mode: 'instant' | 'schedule';
  scheduled_time?: string;
  created_at: string;
}

export interface GenerationJob {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  mode: string;
  generated_post_ids: string[];
  error?: string;
}

export type ApiError = {
  code: string;
  message: string;
};
```

---

## Security Considerations
- `hashed_password` must NEVER appear in any API response — enforce at repository level
- LinkedIn `access_token` must NEVER appear in API responses — strip before returning
- All `ObjectId` conversions must be wrapped in try/except to prevent 500s from malformed IDs

---

## Environment Variables
No new variables in this phase.

---

## Third-Party Services Required
| Service | Purpose |
|---------|---------|
| MongoDB (running from Phase 00) | Data storage |

---

## Implementation Steps (Exact Order)

1. Create `app/models/` directory with all model files
2. Create `app/repositories/base.py` with `BaseRepository`
3. Create all 5 repository files
4. Update `app/core/database.py` to add `create_indexes()` function
5. Add `await create_indexes(db_instance.db)` inside `lifespan` after `connect_db()`
6. Create `app/models/user.py`, `project.py`, `post.py`, `generation_job.py`
7. Create `src/types/index.ts` in frontend
8. Write tests for repository layer
9. Run `pytest tests/` → all pass
10. Commit: `git commit -m "Phase 01: Database design & repository layer"`

---

## Testing Strategy

```python
# tests/test_repositories.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_user_repository_find_by_email():
    # Use mongomock or mock get_db()
    pass

@pytest.mark.asyncio
async def test_soft_delete():
    # Verify deleted=True, deleted_at is set
    pass

@pytest.mark.asyncio
async def test_find_many_excludes_deleted():
    # Ensure deleted=True docs are excluded
    pass
```

---

## Edge Cases
- `ObjectId(invalid_string)` → wrap all conversions in try/except → raise `AppException(code="INVALID_ID")`
- `find_by_id` on non-existent doc → return `None`, handle in service layer
- `readme_context` must be truncated to 4000 chars before storing (prevent oversized documents)
- `daily_generation_reset_at` must be checked before allowing generation in rate limiter

---

## Deliverables / Checklist

- [ ] `BaseRepository` with all generic CRUD methods
- [ ] `UserRepository` with `find_by_email`, `update_linkedin_integration`
- [ ] `ProjectRepository` with `find_by_user`, `update_analysis_cache`
- [ ] `PostRepository` with `find_scheduled_pending`, `update_status`, `increment_retry`
- [ ] `GenerationJobRepository` with `mark_completed`, `mark_failed`
- [ ] All Pydantic models created
- [ ] TypeScript interfaces created in frontend
- [ ] MongoDB indexes created on startup
- [ ] Repository unit tests written
- [ ] All tests pass

---

## Definition of Completion
All 5 repositories instantiable. MongoDB indexes verified in Atlas/Compass. `UserRepository.find_by_email("test@test.com")` returns `None` without errors. All Pydantic models validate correctly. TypeScript interfaces match backend response shapes exactly.