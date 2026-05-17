# PHASE 11 — Workspace APIs & Post Management

## Phase Goal
Build the Workspace — the central hub where users see ALL their generated and posted content across both modes. Includes stats dashboard, post history, search/filter, settings page (LinkedIn connection management, account), and structured error responses for the entire API.

---

## Features Implemented
- `GET /workspace/stats` — User stats (total generated, published, scheduled, projects)
- Settings page with LinkedIn connect/disconnect
- Workspace page: all posts with filter by status/platform
- Post detail page (view + edit)
- Account settings (update name/email)
- Full structured error standardization across all routes
- Settings page — account info, integrations

---

## Technical Architecture

```
Backend:
app/api/v1/routes/
├── workspace.py          ← /workspace/stats
├── integrations.py       ← (Phase 06) extended
└── accounts.py           ← /account/me (update profile)

Frontend:
src/app/dashboard/
├── workspace/
│   └── page.tsx          ← All posts with filters
└── settings/
    └── page.tsx          ← LinkedIn, account settings
```

---

## Backend: Workspace Stats

### Route (`app/api/v1/routes/workspace.py`)
```python
from fastapi import APIRouter, Depends
from bson import ObjectId
from app.dependencies.auth import get_current_user
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.generation_job_repository import GenerationJobRepository

router = APIRouter(prefix="/workspace", tags=["Workspace"])

@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    post_repo = PostRepository()
    project_repo = ProjectRepository()
    job_repo = GenerationJobRepository()

    user_filter = {"user_id": ObjectId(user_id)}

    total_posts = await post_repo.count(user_filter)
    published = await post_repo.count({**user_filter, "status": "posted"})
    scheduled = await post_repo.count({**user_filter, "status": "scheduled"})
    failed = await post_repo.count({**user_filter, "status": "failed"})
    total_projects = await project_repo.count(user_filter)
    total_jobs = await job_repo.count(user_filter)

    return {
        "total_posts_generated": total_posts,
        "total_published": published,
        "total_scheduled": scheduled,
        "total_failed": failed,
        "total_projects": total_projects,
        "total_generation_jobs": total_jobs,
        "plan": current_user.get("plan", "free"),
    }
```

### Account Route (`app/api/v1/routes/accounts.py`)
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.dependencies.auth import get_current_user
from app.repositories.user_repository import UserRepository
from app.core.exceptions import AppException

router = APIRouter(prefix="/account", tags=["Account"])

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None

@router.put("/me")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    repo = UserRepository()
    update_data = {}
    if data.name:
        if len(data.name.strip()) < 2:
            raise AppException("INVALID_NAME", "Name must be at least 2 characters.", 400)
        update_data["name"] = data.name.strip()
    
    if not update_data:
        raise AppException("NO_CHANGES", "No fields to update.", 400)
    
    await repo.update_one(current_user["id"], update_data)
    updated = await repo.find_by_id(current_user["id"])
    updated.pop("hashed_password", None)
    return updated
```

### Register Routers in `api_router`
```python
from app.api.v1.routes.workspace import router as workspace_router
from app.api.v1.routes.accounts import router as accounts_router
api_router.include_router(workspace_router)
api_router.include_router(accounts_router)
```

---

## Structured Error Standardization

All errors across the API must follow this shape. Register in `app/main.py`:

```python
# app/main.py — add these handlers

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = " → ".join(str(loc) for loc in first_error.get("loc", []))
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": f"Validation failed on field: {field}. {first_error.get('msg', '')}",
            "details": errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail)}
    )

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
    )
```

---

## Frontend: Workspace Page (`src/app/dashboard/workspace/page.tsx`)
```tsx
'use client';
import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, Linkedin, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

const STATUS_OPTIONS = ['all', 'generated', 'scheduled', 'posted', 'failed'];

export default function WorkspacePage() {
  const [posts, setPosts] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    api.get('/workspace/stats').then(r => setStats(r.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = filter !== 'all' ? `?status=${filter}` : '';
    api.get(`/posts${params}`).then(r => {
      setPosts(r.data.items);
      setLoading(false);
    });
  }, [filter]);

  return (
    <div className="max-w-4xl mx-auto py-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold mb-1">Workspace</h1>
        <p className="text-muted-foreground text-sm">All your generated content in one place.</p>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Generated', value: stats.total_posts_generated },
            { label: 'Published', value: stats.total_published },
            { label: 'Scheduled', value: stats.total_scheduled },
            { label: 'Projects', value: stats.total_projects },
          ].map(s => (
            <div key={s.label} className="bg-muted/40 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Filter by status:</span>
        <Select defaultValue="all" onValueChange={setFilter}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map(s => (
              <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Posts List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : posts.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          No posts found.
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map(post => (
            <WorkspacePostCard key={post.id} post={post} onUpdate={() => {
              api.get(`/posts?${filter !== 'all' ? `status=${filter}` : ''}`).then(r => setPosts(r.data.items));
            }} />
          ))}
        </div>
      )}
    </div>
  );
}

function WorkspacePostCard({ post, onUpdate }: { post: any; onUpdate: () => void }) {
  const { toast } = useToast();
  const [publishing, setPublishing] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(post.content);
    toast({ title: 'Copied!' });
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      await api.post(`/publish/${post.id}`);
      toast({ title: '🎉 Published to LinkedIn!' });
      onUpdate();
    } catch (err: any) {
      toast({ title: 'Publish failed', description: err.response?.data?.message, variant: 'destructive' });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="border rounded-xl p-4 bg-card space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{new Date(post.created_at).toLocaleDateString()}</span>
          <span>·</span>
          <span className="capitalize">{post.mode} mode</span>
          {post.angle && <><span>·</span><span>{post.angle.replace('_', ' ')}</span></>}
        </div>
        <Badge variant={post.status === 'posted' ? 'secondary' : post.status === 'failed' ? 'destructive' : 'default'}>
          {post.status}
        </Badge>
      </div>

      <p className={`text-sm leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>
        {post.content}
      </p>

      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => setExpanded(v => !v)} className="text-xs text-muted-foreground hover:text-foreground underline">
          {expanded ? 'Show less' : 'Show more'}
        </button>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" onClick={handleCopy} className="h-7 gap-1.5 text-xs">
            <Copy className="w-3 h-3" /> Copy
          </Button>
          {(post.status === 'generated' || post.status === 'draft') && (
            <Button size="sm" onClick={handlePublish} disabled={publishing}
              className="h-7 gap-1.5 text-xs bg-[#0077B5] hover:bg-[#006097]">
              <Linkedin className="w-3 h-3" />
              {publishing ? '...' : 'Publish'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## Frontend: Settings Page (`src/app/dashboard/settings/page.tsx`)
```tsx
'use client';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Linkedin, CheckCircle, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { useToast } from '@/components/ui/use-toast';

export default function SettingsPage() {
  const { user, setAuth, token } = useAuthStore();
  const { toast } = useToast();
  const [linkedinStatus, setLinkedinStatus] = useState<any>(null);
  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  useEffect(() => {
    api.get('/integrations/status').then(r => setLinkedinStatus(r.data.linkedin));
  }, []);

  const handleSaveName = async () => {
    setSaving(true);
    try {
      const res = await api.put('/account/me', { name });
      if (token) setAuth({ ...user!, name: res.data.name }, token);
      toast({ title: 'Name updated.' });
    } catch (err: any) {
      toast({ title: 'Update failed', description: err.response?.data?.message, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnectLinkedIn = async () => {
    if (!confirm('Disconnect LinkedIn? Scheduled posts will fail to publish.')) return;
    setDisconnecting(true);
    try {
      await api.delete('/integrations/linkedin/disconnect');
      setLinkedinStatus({ connected: false });
      toast({ title: 'LinkedIn disconnected.' });
    } finally {
      setDisconnecting(false);
    }
  };

  const handleConnectLinkedIn = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/integrations/linkedin/connect`;
  };

  return (
    <div className="max-w-2xl mx-auto py-4 space-y-10">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm">Manage your account and integrations.</p>
      </div>

      {/* Account */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">Account</h2>
        <div>
          <Label>Full Name</Label>
          <div className="flex gap-3 mt-1.5">
            <Input value={name} onChange={e => setName(e.target.value)} className="flex-1" />
            <Button onClick={handleSaveName} disabled={saving} variant="outline">
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
        <div>
          <Label>Email</Label>
          <Input value={user?.email || ''} disabled className="mt-1.5 bg-muted" />
          <p className="text-xs text-muted-foreground mt-1">Email cannot be changed.</p>
        </div>
        <div>
          <Label>Plan</Label>
          <div className="mt-1.5">
            <Badge variant={user?.plan === 'premium' ? 'default' : 'secondary'}>
              {user?.plan === 'premium' ? '⭐ Premium' : 'Free'}
            </Badge>
            {user?.plan === 'free' && (
              <p className="text-xs text-muted-foreground mt-2">
                Free plan: 5 generations/day. Upgrade for unlimited access.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Integrations */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">Integrations</h2>

        {/* LinkedIn */}
        <div className="border rounded-xl p-5 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#0077B5]/10 rounded-lg flex items-center justify-center">
              <Linkedin className="w-5 h-5 text-[#0077B5]" />
            </div>
            <div>
              <p className="font-medium">LinkedIn</p>
              {linkedinStatus?.connected ? (
                <div className="flex items-center gap-1.5 text-xs text-green-600 mt-0.5">
                  <CheckCircle className="w-3 h-3" />
                  Connected{linkedinStatus.connected_at && ` · ${new Date(linkedinStatus.connected_at).toLocaleDateString()}`}
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                  <AlertCircle className="w-3 h-3" />
                  Not connected
                </div>
              )}
            </div>
          </div>

          {linkedinStatus?.connected ? (
            <Button
              size="sm"
              variant="outline"
              onClick={handleDisconnectLinkedIn}
              disabled={disconnecting}
              className="text-destructive hover:text-destructive"
            >
              {disconnecting ? 'Disconnecting...' : 'Disconnect'}
            </Button>
          ) : (
            <Button size="sm" onClick={handleConnectLinkedIn} className="bg-[#0077B5] hover:bg-[#006097]">
              Connect
            </Button>
          )}
        </div>
      </section>
    </div>
  );
}
```

---

## API Endpoints Added This Phase

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/workspace/stats` | ✅ | User stats summary |
| PUT | `/api/v1/account/me` | ✅ | Update user profile |

---

## Implementation Steps (Exact Order)

1. Create `app/api/v1/routes/workspace.py`
2. Create `app/api/v1/routes/accounts.py`
3. Register both in `api_router`
4. Add all global exception handlers to `app/main.py`
5. Test `/workspace/stats` — verify counts are accurate
6. Test 422 validation error → returns `VALIDATION_ERROR` code
7. Test 500 unhandled error → returns `INTERNAL_ERROR` code
8. Create `src/app/dashboard/workspace/page.tsx`
9. Create `src/app/dashboard/settings/page.tsx`
10. Test Workspace: filter by status works
11. Test Settings: name update works, LinkedIn connect/disconnect works
12. Commit: `git commit -m "Phase 11: Workspace APIs, settings, structured errors"`

---

## Deliverables / Checklist

- [ ] `GET /workspace/stats` returns correct counts
- [ ] `PUT /account/me` updates name
- [ ] All errors return `{ code, message }` format
- [ ] 422 validation errors formatted correctly
- [ ] Unhandled 500 errors return `INTERNAL_ERROR` (not stack trace)
- [ ] Workspace page shows stats row
- [ ] Workspace posts filter by status
- [ ] Copy + Publish buttons work in workspace
- [ ] Settings page: name edit works
- [ ] Settings page: LinkedIn connected status shown
- [ ] Settings page: Connect / Disconnect LinkedIn works

---

## Definition of Completion
`/workspace/stats` returns accurate counts. The Workspace page shows all user posts with working status filter. Settings page shows account info and LinkedIn connection state. All API errors system-wide follow `{ code, message }` format — no raw Python tracebacks ever exposed.