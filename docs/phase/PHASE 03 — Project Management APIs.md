# PHASE 03 — Project Management APIs

## Phase Goal
Build complete CRUD for the `projects` collection. Users can create, list, view, update, and soft-delete their projects. Projects are the core input unit — every AI generation in later phases originates from a project.

---

## Features Implemented
- Create a project (with GitHub URL or manual README)
- List all projects for the authenticated user (paginated)
- Get a single project by ID
- Update a project
- Soft delete a project
- README auto-truncation to 4000 chars on save
- Frontend: Project creation form (Step 1 of Instant Mode)
- Frontend: Projects list page in workspace

---

## Technical Architecture

```
app/
├── api/v1/routes/
│   └── projects.py           ← All project endpoints
├── services/
│   └── project_service.py    ← Business logic for projects
├── repositories/
│   └── project_repository.py ← (from Phase 01)
└── models/
    └── project.py            ← Request/Response Pydantic models
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/projects` | ✅ | Create new project |
| GET | `/api/v1/projects` | ✅ | List user's projects (paginated) |
| GET | `/api/v1/projects/:id` | ✅ | Get single project |
| PUT | `/api/v1/projects/:id` | ✅ | Update project |
| DELETE | `/api/v1/projects/:id` | ✅ | Soft delete project |

---

## Request / Response Shapes

### POST `/projects`
**Request:**
```json
{
  "title": "AgriLenses",
  "github_url": "https://github.com/user/agrilenses",
  "readme_context": "# AgriLenses\nA ML-powered crop disease detection app...",
  "problem_solved": "Farmers cannot detect crop diseases early without expert help.",
  "tech_stack": ["Python", "TensorFlow", "FastAPI", "React"],
  "features": ["Disease detection", "92% accuracy model", "Mobile-friendly UI"],
  "results_impact": "Reduced crop loss by 30% in a 50-farmer pilot study."
}
```
**Response 201:**
```json
{
  "id": "667abc...",
  "user_id": "667def...",
  "title": "AgriLenses",
  "github_url": "https://github.com/user/agrilenses",
  "problem_solved": "Farmers cannot detect crop diseases early without expert help.",
  "tech_stack": ["Python", "TensorFlow", "FastAPI", "React"],
  "features": ["Disease detection", "92% accuracy model"],
  "results_impact": "Reduced crop loss by 30%...",
  "has_analysis_cache": false,
  "created_at": "2025-01-01T..."
}
```

### GET `/projects`
**Query params:** `?skip=0&limit=10`

**Response 200:**
```json
{
  "items": [ ...ProjectResponse ],
  "total": 3,
  "skip": 0,
  "limit": 10
}
```

### DELETE `/projects/:id`
**Response 200:**
```json
{ "message": "Project deleted successfully." }
```
**Errors:**
```json
{ "code": "PROJECT_NOT_FOUND", "message": "Project not found." }
{ "code": "FORBIDDEN", "message": "You do not have access to this project." }
```

---

## Backend Tasks

### 1. Project Models (`app/models/project.py`)
```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    github_url: Optional[str] = None
    readme_context: Optional[str] = None
    problem_solved: str = Field(..., min_length=10, max_length=2000)
    tech_stack: List[str] = Field(..., min_items=1, max_items=20)
    features: Optional[List[str]] = Field(None, max_items=10)
    results_impact: Optional[str] = Field(None, max_length=1000)

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    github_url: Optional[str] = None
    readme_context: Optional[str] = None
    problem_solved: Optional[str] = Field(None, min_length=10)
    tech_stack: Optional[List[str]] = None
    features: Optional[List[str]] = None
    results_impact: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    github_url: Optional[str]
    problem_solved: str
    tech_stack: List[str]
    features: Optional[List[str]]
    results_impact: Optional[str]
    has_analysis_cache: bool = False
    created_at: datetime
    updated_at: datetime

class PaginatedProjects(BaseModel):
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int
```

### 2. Project Service (`app/services/project_service.py`)
```python
from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.project_repository import ProjectRepository
from app.core.exceptions import AppException
from app.models.project import ProjectCreate, ProjectUpdate

README_MAX_CHARS = 4000

class ProjectService:
    def __init__(self):
        self.repo = ProjectRepository()

    def _truncate_readme(self, readme: str) -> str:
        if len(readme) > README_MAX_CHARS:
            return readme[:README_MAX_CHARS] + "\n...[truncated]"
        return readme

    async def create_project(self, user_id: str, data: ProjectCreate) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": ObjectId(user_id),
            "title": data.title.strip(),
            "github_url": data.github_url,
            "readme_context": self._truncate_readme(data.readme_context) if data.readme_context else None,
            "problem_solved": data.problem_solved.strip(),
            "tech_stack": [t.strip() for t in data.tech_stack],
            "features": data.features or [],
            "results_impact": data.results_impact,
            "analysis_cache": None,
            "created_at": now,
            "updated_at": now,
            "deleted": False,
            "deleted_at": None
        }
        project_id = await self.repo.insert_one(doc)
        return await self.repo.find_by_id(project_id)

    async def get_projects(self, user_id: str, skip: int, limit: int) -> dict:
        from bson import ObjectId
        items = await self.repo.find_by_user(user_id, skip, limit)
        total = await self.repo.count({"user_id": ObjectId(user_id)})
        # Add computed field
        for item in items:
            item["has_analysis_cache"] = item.get("analysis_cache") is not None
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get_project(self, project_id: str, user_id: str) -> dict:
        project = await self.repo.find_by_id(project_id)
        if not project:
            raise AppException("PROJECT_NOT_FOUND", "Project not found.", 404)
        if project["user_id"] != user_id:
            raise AppException("FORBIDDEN", "You do not have access to this project.", 403)
        project["has_analysis_cache"] = project.get("analysis_cache") is not None
        return project

    async def update_project(
        self, project_id: str, user_id: str, data: ProjectUpdate
    ) -> dict:
        project = await self.get_project(project_id, user_id)  # validates ownership
        
        update_data = data.model_dump(exclude_none=True)
        if "readme_context" in update_data and update_data["readme_context"]:
            update_data["readme_context"] = self._truncate_readme(update_data["readme_context"])
        
        # Invalidate analysis cache if core project data changes
        core_fields = {"problem_solved", "tech_stack", "readme_context", "github_url"}
        if core_fields & set(update_data.keys()):
            update_data["analysis_cache"] = None
        
        await self.repo.update_one(project_id, update_data)
        return await self.repo.find_by_id(project_id)

    async def delete_project(self, project_id: str, user_id: str) -> None:
        project = await self.get_project(project_id, user_id)  # validates ownership
        await self.repo.soft_delete(project_id)
```

### 3. Project Router (`app/api/v1/routes/projects.py`)
```python
from fastapi import APIRouter, Depends, Query
from app.services.project_service import ProjectService
from app.dependencies.auth import get_current_user
from app.models.project import ProjectCreate, ProjectUpdate, PaginatedProjects

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", status_code=201)
async def create_project(
    data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(ProjectService)
):
    return await service.create_project(current_user["id"], data)

@router.get("")
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(ProjectService)
):
    return await service.get_projects(current_user["id"], skip, limit)

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(ProjectService)
):
    return await service.get_project(project_id, current_user["id"])

@router.put("/{project_id}")
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(ProjectService)
):
    return await service.update_project(project_id, current_user["id"], data)

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(ProjectService)
):
    await service.delete_project(project_id, current_user["id"])
    return {"message": "Project deleted successfully."}
```

### 4. Register in main router
```python
# app/api/v1/router.py
from app.api.v1.routes.projects import router as projects_router
api_router.include_router(projects_router)
```

---

## Frontend Tasks

### 1. Project API calls (`src/lib/projects-api.ts`)
```typescript
import api from './api';
import type { Project } from '@/types';

export const createProject = async (data: Partial<Project>): Promise<Project> => {
  const res = await api.post('/projects', data);
  return res.data;
};

export const getProjects = async (skip = 0, limit = 10) => {
  const res = await api.get(`/projects?skip=${skip}&limit=${limit}`);
  return res.data;
};

export const getProject = async (id: string): Promise<Project> => {
  const res = await api.get(`/projects/${id}`);
  return res.data;
};

export const deleteProject = async (id: string): Promise<void> => {
  await api.delete(`/projects/${id}`);
};
```

### 2. Project Creation Form (`src/components/projects/ProjectForm.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { createProject } from '@/lib/projects-api';

interface Props {
  onCreated: (project: any) => void;
}

export default function ProjectForm({ onCreated }: Props) {
  const [form, setForm] = useState({
    title: '',
    github_url: '',
    problem_solved: '',
    tech_stack: '',
    results_impact: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const project = await createProject({
        ...form,
        tech_stack: form.tech_stack.split(',').map(s => s.trim()).filter(Boolean),
      });
      onCreated(project);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <Label>Project Title *</Label>
        <Input
          value={form.title}
          onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
          placeholder="e.g. AgriLenses"
        />
      </div>
      <div>
        <Label>GitHub URL (optional)</Label>
        <Input
          value={form.github_url}
          onChange={e => setForm(p => ({ ...p, github_url: e.target.value }))}
          placeholder="https://github.com/you/project"
        />
      </div>
      <div>
        <Label>Problem Solved *</Label>
        <Textarea
          value={form.problem_solved}
          onChange={e => setForm(p => ({ ...p, problem_solved: e.target.value }))}
          placeholder="What problem does your project solve?"
          rows={3}
        />
      </div>
      <div>
        <Label>Tech Stack * (comma-separated)</Label>
        <Input
          value={form.tech_stack}
          onChange={e => setForm(p => ({ ...p, tech_stack: e.target.value }))}
          placeholder="Python, FastAPI, React, MongoDB"
        />
      </div>
      <div>
        <Label>Results / Impact (optional)</Label>
        <Input
          value={form.results_impact}
          onChange={e => setForm(p => ({ ...p, results_impact: e.target.value }))}
          placeholder="e.g. 92% accuracy, 30% reduction in crop loss"
        />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button onClick={handleSubmit} disabled={loading} className="w-full">
        {loading ? 'Saving project...' : 'Save & Continue'}
      </Button>
    </div>
  );
}
```

---

## AI Workflow Tasks
None — `analysis_cache` is set to `null` on creation; will be populated by AI pipeline in Phase 05.

---

## Scheduler / Background Tasks
None in this phase.

---

## Security Considerations
- Every GET/PUT/DELETE must verify `project.user_id === current_user.id` — enforced in service
- `project_id` param must be valid ObjectId — wrap in try/except → `AppException("INVALID_ID")`
- `readme_context` truncated to 4000 chars — prevents oversized DB writes AND future token explosion

---

## Environment Variables
No new variables.

---

## Third-Party Services Required
None new.

---

## Implementation Steps (Exact Order)

1. Create `app/models/project.py` with all models
2. Create `app/services/project_service.py`
3. Create `app/api/v1/routes/projects.py`
4. Register projects router in `app/api/v1/router.py`
5. Test all endpoints via Swagger UI (`/docs`)
6. Verify ownership check: create project with User A, try GET with User B → 403
7. Verify soft delete: deleted project doesn't appear in list
8. Verify `analysis_cache` invalidated on core field update
9. Create `src/lib/projects-api.ts`
10. Create `ProjectForm` component
11. Create `/dashboard/projects` page showing list + create form
12. Test end-to-end: create project from frontend → appears in list
13. Commit: `git commit -m "Phase 03: Project management APIs"`

---

## Testing Strategy

```python
# tests/test_projects.py
@pytest.mark.asyncio
async def test_create_project_success():
    # Mock auth + project repo
    # POST /projects → 201

@pytest.mark.asyncio
async def test_get_project_forbidden():
    # Create project with user_A
    # GET with user_B → 403, code=FORBIDDEN

@pytest.mark.asyncio
async def test_readme_truncation():
    # Input 5000 char readme
    # Stored readme should be <= 4000 chars + "[truncated]"

@pytest.mark.asyncio
async def test_soft_delete_not_in_list():
    # Delete project
    # GET /projects → deleted project not in items
```

---

## Edge Cases
- `tech_stack: []` → Pydantic validation error 422
- `problem_solved: ""` or less than 10 chars → 422
- Invalid ObjectId in URL → handle with try/except → `AppException("INVALID_ID", 400)`
- Update with empty `readme_context: ""` → set to `None`, not empty string
- User deletes project that has scheduled posts → posts remain but project is soft-deleted; handle in AI pipeline (Phase 05)

---

## Deliverables / Checklist

- [ ] POST `/projects` creates project → 201 with response
- [ ] GET `/projects` lists only current user's non-deleted projects
- [ ] GET `/projects/:id` returns project with ownership check
- [ ] PUT `/projects/:id` updates and invalidates `analysis_cache` on core field change
- [ ] DELETE `/projects/:id` soft deletes (project still in DB with `deleted: true`)
- [ ] `readme_context` auto-truncated to 4000 chars
- [ ] Invalid ObjectId → proper error returned (not 500)
- [ ] Frontend `ProjectForm` component working
- [ ] End-to-end create → list → delete working from UI
- [ ] All tests passing

---

## Definition of Completion
Authenticated user can create a project, see it in the list, update it, and soft-delete it. Unauthenticated requests return 401. Accessing another user's project returns 403. Frontend form correctly submits to API.