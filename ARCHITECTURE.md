# Social Media Automation Platform - Architecture & Design

## System Overview

This document explains the WHAT, WHY, and HOW of our system architecture.

---

## 1. Why This Architecture?

### Principle: Simplicity First
- **No microservices**: All in one backend. Microservices add complexity; we don't need that yet.
- **No Kubernetes**: Docker Compose suffices for local development and simple deployment.
- **No event bus**: Direct scheduling with APScheduler is simple and reliable for a single machine.
- **MongoDB over PostgreSQL**: You already know MongoDB, and it's flexible for evolving schema.

### Key Design Decisions

| Decision                  | Why                                                    | What We Avoid                          |
| ------------------------- | ------------------------------------------------------ | -------------------------------------- |
| **Async FastAPI**         | Handle multiple requests + background jobs efficiently | Blocking I/O, thread pools             |
| **APScheduler**           | Simple in-memory job scheduling for daily posts        | Celery + Redis (overkill for MVP)      |
| **Motor (async MongoDB)** | Non-blocking database queries                          | Synchronous pymongo, connection issues |
| **OAuth2 + JWT**          | Standard, secure, easy to extend                       | Custom auth, session management        |
| **Single app.py**         | Easy to understand startup flow                        | Complex initialization across files    |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                    │
│              Dashboard + Schedule + OAuth Login           │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────────┐
│                  BACKEND (FastAPI)                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  API Routes (auth, posts, health)                       │
│         ↓                                                │
│  Authentication Service (OAuth2, JWT)                   │
│         ↓                                                │
│  Post Service (CRUD, LinkedIn integration)              │
│         ↓                                                │
│  Scheduler Service (APScheduler - runs jobs daily)      │
│         ↓                                                │
│  Database Service (MongoDB via Motor)                   │
│                                                           │
└────────────────────┬────────────────────────────────────┘
                     │ REST/OAuth
        ┌────────────┼────────────┐
        │            │            │
    ┌───▼──┐    ┌────▼────┐  ┌──▼──────┐
    │ OAuth│    │LinkedIn │  │MongoDB  │
    │ Flow │    │ API     │  │ Atlas   │
    └──────┘    └─────────┘  └─────────┘
```

---

## 3. How the Posting Workflow Works

### 3.1 User schedules a post:

```
1. User logs in (OAuth2 → LinkedIn)
   ├─ Frontend redirects to LinkedIn login
   ├─ LinkedIn returns auth code
   ├─ Backend exchanges code for access token
   └─ Backend stores token + user in MongoDB

2. User creates and schedules a post
   ├─ Frontend sends POST to /api/posts
   ├─ Backend stores post in MongoDB
   └─ APScheduler registers the post for scheduled time

3. At scheduled time, APScheduler triggers the post
   ├─ Retrieves post from MongoDB
   ├─ Calls LinkedIn API to publish
   ├─ Stores result (success/failure) in MongoDB
   ├─ If fails, retries (up to 3 times with backoff)
   └─ Logs everything to file

4. Frontend dashboard shows post status in real-time
   ├─ User can see posted/scheduled/failed posts
   ├─ Can retry failed posts manually
   └─ Can delete scheduled posts
```

---

## 4. Key Components Explained

### 4.1 **Authentication Service**
**File**: `app/services/auth_service.py`
- Handles OAuth2 flow with LinkedIn
- Creates JWT tokens for session management
- Validates tokens on each API request
- Stores user + LinkedIn access tokens in MongoDB

**Why separate?**
- Authentication logic is complex; keeping it separate makes it testable and reusable
- Easier to add new OAuth providers later (Instagram, Twitter)

### 4.2 **Post Service**
**File**: `app/services/post_service.py`
- CRUD operations (Create, Read, Update, Delete) for posts
- Validates post data (length, links, etc.)
- Calls LinkedIn API to publish
- Handles retries on failure

**Why separate?**
- Business logic isolated from API routes
- Easy to test independently
- Reusable across different endpoints

### 4.3 **Scheduler Service**
**File**: `app/scheduler/scheduler.py`
- Manages APScheduler instance
- Registers jobs for each scheduled post
- Triggers posts at scheduled time
- Implements exponential backoff for retries

**Why separate?**
- Scheduling logic can be complex; keeping it isolated prevents bugs
- Easy to add new job types (cleanup, analytics, etc.)

### 4.4 **Database Service**
**File**: `app/db/mongodb.py`
- Connection pooling to MongoDB Atlas
- Async queries via Motor
- Helper functions for common operations

**Why?**
- Centralized connection management
- Prevents connection leaks
- Easy to add caching later

### 4.5 **Models**
**File**: `app/models/schemas.py`
- Pydantic models for validation
- Database schemas for MongoDB
- Type hints for everything

**Why Pydantic?**
- Automatic validation + serialization
- Clear API contracts
- Generates OpenAPI docs automatically

---

## 5. Database Schema (MongoDB)

### Users Collection
```json
{
  "_id": ObjectId,
  "email": "user@linkedin.com",
  "name": "John Doe",
  "linkedin_id": "12345",
  "linkedin_access_token": "encrypted_token",
  "token_expiry": ISODate("2026-05-15"),
  "created_at": ISODate("2026-05-08"),
  "updated_at": ISODate("2026-05-08")
}
```

### Posts Collection
```json
{
  "_id": ObjectId,
  "user_id": ObjectId (ref to Users),
  "content": "My scheduled post...",
  "scheduled_time": ISODate("2026-05-09T10:00:00Z"),
  "status": "scheduled",  // scheduled, posted, failed, draft
  "linkedin_post_id": "urn:li:share:123456",
  "platform": "linkedin",
  "retry_count": 0,
  "last_error": null,
  "created_at": ISODate("2026-05-08"),
  "posted_at": null
}
```

---

## 6. API Endpoints (MVP)

| Method | Endpoint                | Purpose                 | Auth |
| ------ | ----------------------- | ----------------------- | ---- |
| GET    | `/auth/login`           | LinkedIn OAuth redirect | No   |
| GET    | `/auth/callback`        | OAuth callback handler  | No   |
| POST   | `/api/posts`            | Create scheduled post   | JWT  |
| GET    | `/api/posts`            | List user's posts       | JWT  |
| GET    | `/api/posts/{id}`       | Get post details        | JWT  |
| PUT    | `/api/posts/{id}`       | Update post             | JWT  |
| DELETE | `/api/posts/{id}`       | Delete post             | JWT  |
| POST   | `/api/posts/{id}/retry` | Retry failed post       | JWT  |
| GET    | `/health`               | Health check            | No   |

---

## 7. How APScheduler Works (Simplified)

```python
# When user schedules a post for 10 AM:
scheduler.add_job(
    post_to_linkedin,           # Function to call
    'cron',                      # Job type
    hour=10, minute=0,           # Time
    id='post_12345',             # Unique ID
    args=[post_id]               # Arguments
)

# At 10 AM, APScheduler calls post_to_linkedin(post_id)
# If it fails, we catch exception and retry with backoff

# When user deletes post:
scheduler.remove_job('post_12345')  # Job is cancelled
```

**Why not Celery + Redis?**
- Celery requires Redis (extra infrastructure)
- For MVP on a single machine, APScheduler is simpler
- Easier to understand and debug
- Good enough for 100-1000 scheduled posts

---

## 8. MVP Features (Phase 1)

✅ **Must Have**:
- LinkedIn OAuth login
- Create scheduled posts
- Auto-post at scheduled time
- List/view posts
- Delete scheduled posts
- Basic retry logic
- Error logging

⏭️ **Phase 2**:
- Manual retry from dashboard
- Post status updates
- Edit scheduled posts
- Delete posted content

⏭️ **Phase 3**:
- Instagram integration
- Twitter/X integration
- AI content generation
- Analytics dashboard

---

## 9. Error Handling & Retries

**Strategy**: Exponential backoff

```
Attempt 1: Fail → Wait 5 seconds
Attempt 2: Fail → Wait 25 seconds (5^2)
Attempt 3: Fail → Wait 125 seconds (5^3)
Attempt 4+: Mark as failed, notify user
```

**Why?**
- Handles temporary API outages gracefully
- Doesn't hammer LinkedIn API
- Production systems expect this pattern
- Easy to explain to non-technical people

---

## 10. Logging Strategy

**We log**:
- ✅ User login/logout
- ✅ Post scheduled/posted/failed
- ✅ API errors + stack traces
- ✅ Retry attempts + reasons
- ✅ LinkedIn API responses (errors only)

**We DON'T log**:
- ❌ User tokens (security risk)
- ❌ API key/secrets
- ❌ Every database query (too verbose)

---

## 11. Development Workflow

### Phase 1: Setup (This Session)
- [ ] Create backend folder structure
- [ ] Setup MongoDB Atlas
- [ ] Create requirements.txt + environment setup
- [ ] Implement basic FastAPI app

### Phase 2: Authentication (Next Session)
- [ ] Implement OAuth2 with LinkedIn
- [ ] JWT token management
- [ ] Secure token storage

### Phase 3: Post Management
- [ ] Create Post model
- [ ] Build Post CRUD API
- [ ] Implement post validation

### Phase 4: Scheduling
- [ ] Setup APScheduler
- [ ] Implement post publishing job
- [ ] Add retry logic

### Phase 5: LinkedIn Integration
- [ ] Authenticate with LinkedIn API
- [ ] Implement post publishing
- [ ] Handle LinkedIn errors

### Phase 6: Frontend Dashboard
- [ ] Next.js setup
- [ ] Login page (OAuth redirect)
- [ ] Post creation form
- [ ] Posts list view

---

## 12. Why This Setup Will Teach You Production Engineering

| Concept              | What You'll Learn                             | Real-World Use                             |
| -------------------- | --------------------------------------------- | ------------------------------------------ |
| **Async I/O**        | Non-blocking requests, efficient resource use | Any modern web service                     |
| **Job Scheduling**   | Background jobs, cron tasks, retries          | Email newsletters, data sync, cleanup jobs |
| **OAuth2**           | Secure third-party integration                | Any API that uses Facebook/Google login    |
| **Retry Logic**      | Handling failures gracefully                  | Distributed systems, external APIs         |
| **Logging**          | Debugging production issues                   | Every production system ever               |
| **Modular Services** | Clean architecture, testability               | Enterprise codebases                       |

---

## 13. Future Scaling (Don't Do Yet!)

When you need to scale:

**Bottleneck 1**: Too many scheduled jobs
→ Move scheduler to separate service + use job queue

**Bottleneck 2**: Too many database queries
→ Add caching layer (Redis)

**Bottleneck 3**: Deployment complexity
→ Docker Compose → Railway/Render

**Bottleneck 4**: Multiple machines needed
→ Then consider microservices + event bus

---

## 14. File Structure Explanation

```
backend/
├── app/
│   ├── api/                  # API routes
│   │   └── routes.py         # All endpoints in one file (simple!)
│   ├── services/             # Business logic (auth, posts, etc.)
│   │   ├── auth_service.py
│   │   └── post_service.py
│   ├── scheduler/            # APScheduler setup
│   │   └── scheduler.py
│   ├── models/               # Pydantic + database schemas
│   │   └── schemas.py
│   ├── db/                   # Database connection
│   │   └── mongodb.py
│   ├── utils/                # Helpers (logger, config, etc.)
│   │   ├── logger.py
│   │   └── config.py
│   └── main.py               # FastAPI app initialization
├── .env                      # Environment variables (git-ignored)
├── .env.example              # Template for .env
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker setup
└── README.md                 # Getting started guide
```

**Why?**
- Each folder has ONE responsibility
- Easy to find code: need auth? → services/auth_service.py
- New developer can understand structure in 5 minutes
- Easy to add new features (new service = new file)

---

## Summary

This architecture is designed for:
✅ Easy to understand (start simple)
✅ Easy to extend (modular services)
✅ Production-grade (proper error handling, logging, retry logic)
✅ Learning-focused (clear why each piece exists)
❌ NOT enterprise scale (no microservices, no complex infrastructure)

The goal: Build a system that works, that YOU understand deeply, and that teaches you real production engineering concepts.

Ready to build? Let's start! 🚀
