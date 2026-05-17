# AI Career Visibility Platform — Senior SDE System Design Document (MVP v1.1 & Beyond)

## Scope of THIS MVP & Architecture

You ONLY want:
* User Account Creation & Management
* Social Media Integrations (LinkedIn initially, extensible to Instagram, GitHub)
* Instant Post Generation & Posting
* Scheduled Post Automation
* AI Project Understanding
* Student-focused workflow

NOT included now:
* Resume bullets
* Portfolio summaries
* Recruiter pitch
* Advanced Analytics engine
* Team collaboration
* Advanced AI memory

---

## 1. SYSTEM OVERVIEW

### Product Goal
Student inputs:
* project title
* GitHub repo / README
* problem solved
* tech stack

System:
* understands project
* generates platform-specific posts
* lets user select target platform(s) (LinkedIn now, Insta/GitHub later)
* optionally schedules posts or posts instantly
* auto-posts to the selected connected social platforms

---

## 2. CORE BACKEND ARCHITECTURE (Current Tech Stack)

```text
Frontend (Next.js 14, Tailwind v4, Shadcn UI)
        ↓
FastAPI Backend (Async Python)
        ↓
Core Services Layer
 ├── Auth Service (User Identity)
 ├── Integrations Service (Social OAuth Tokens)
 ├── AI Pipeline (Analyzer, Strategy, Generator, Humanizer)
 ├── Scheduling Service (APScheduler)
 ├── Platform Services (LinkedIn, Insta...)
        ↓
MongoDB (Async via Motor)
```

### Senior Founder/SDE Architecture Decisions:
1. **No Celery/Redis for MVP**: We use **APScheduler** for in-memory, reliable background task scheduling with exponential backoff.
2. **MongoDB Schema**: Social media APIs frequently change their payload structures, and different platforms require storing different token shapes.
3. **Model Agnostic AI Client**: The system must easily swap between HuggingFace (current), Gemini, or GPT without breaking core generation flows.

---

## 3. ADVANCED ARCHITECTURAL IMPROVEMENTS (MVP.v1.1)

To ensure this MVP scales cleanly without technical debt, we have integrated the following advanced patterns:

### A. Content Generation Tracking
AI generation itself must be tracked. This is critical for loading states, analytics, and debugging timeouts.
```json
// Collection: generation_jobs
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "status": "processing", // processing, completed, failed
  "mode": "instant",
  "input_payload": {},
  "generated_post_ids": ["ObjectId"],
  "started_at": "ISODate()",
  "completed_at": null,
  "error": null
}
```

### B. Draft System & Post Lifecycle
A cleaner post state machine.
**Status Flow**: `draft` → `generated` → `scheduled` → `publishing` → `posted` OR `failed`.

### C. APScheduler Production Safety
**CRITICAL LIMITATION**: APScheduler runs in-memory. If the FastAPI server restarts, scheduled jobs vanish.
**SOLUTION**: 
On FastAPI `startup` event, the system **fetches all posts where status = "scheduled"** from MongoDB and re-registers them into APScheduler.

*(Note: Horizontal scaling with multiple FastAPI instances + APScheduler can cause duplicate jobs. This is an acceptable MVP tradeoff, but later requires Redis/Celery).*

### D. Multi-Model AI Abstraction
The system is built to switch seamlessly between `huggingface`, `gemini`, or `gpt`.
```python
class BaseAIClient:
    async def generate(self, prompt: str) -> str: pass

class HuggingFaceClient(BaseAIClient): ...
class GeminiClient(BaseAIClient): ...

def get_ai_client() -> BaseAIClient:
    provider = settings.LLM_PROVIDER # e.g. "huggingface"
    # Returns appropriate client instance
```

### E. AI Cost & Context Optimization
1. **Input Token Guard**: Before sending a README to the LLM, the system truncates and summarizes the input. This prevents token explosion and API costs.
2. **Project Context Cache**: Avoid re-analyzing the same project multiple times.
```json
// Inside projects collection
{
  "analysis_cache": {
    "problem": "...",
    "technical_depth": "...",
    "angles": []
  }
}
```

### F. Prompt Versioning & Quality Control
Every generated post records the `prompt_version` (e.g., `"v1.2"`) allowing for A/B testing of prompt quality and easy rollbacks if AI quality degrades.

### G. Content Angle Engine
This is the **real differentiation**. Instead of a generic prompt, we use an Angle Engine.
* **Angles**: Achievement, Storytelling, Learning, Technical Breakdown, Problem-Solution, Internship Focused.
* **Flow**: `Project Analysis -> Best Angle Selection -> Hook Generation -> Post Generation`.

### H. Humanization Rules
Enforced explicitly in the AI Humanizer Layer.
* **Banned AI Phrases Removed Automatically**: "delve", "excited to announce", "in today's fast-paced world", "unlocking potential".

---

## 4. DATABASE DESIGN (MongoDB Schema)

We implement **Soft Deletes** (`deleted: boolean`) across all primary collections to prevent permanent data loss.

### Collection: `users`
```json
{
  "_id": "ObjectId",
  "name": "John Doe",
  "email": "student@university.edu",
  "created_at": "ISODate()",
  "deleted": false,
  "features": {
    "scheduler_enabled": true
  },
  "integrations": {
    "linkedin": {
      "linkedin_id": "urn:li:person:123",
      "access_token": "token...",
      "connected": true
    }
  }
}
```

### Collection: `projects`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "AI Resume Builder",
  "readme_context": "...",
  "analysis_cache": { "problem": "...", "angles": [] },
  "deleted": false
}
```

### Collection: `posts`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "project_id": "ObjectId",
  "content": "Excited to share my new project...",
  "platforms": ["linkedin"], 
  "status": "scheduled", // draft, generated, scheduled, publishing, posted, failed
  "mode": "schedule",
  "prompt_version": "v1.2",
  "scheduled_time": "ISODate()",
  "posted_at": null,
  "platform_post_ids": {"linkedin": "urn:li:share:123"},
  "retry_count": 0,
  "next_retry_at": null,
  "deleted": false
}
```

---

## 5. PLATFORM ABSTRACTION & FORMATTERS

The system strictly abstracts social platforms and uses Formatters. An AI output isn't directly posted; it goes through a Formatter layer to adjust spacing (LinkedIn) vs Emojis (Instagram).

```text
/services/platforms/
 ├── base_platform.py
 ├── linkedin/
 │    ├── auth.py
 │    ├── publish.py
 │    └── formatter.py
 └── github/
      └── ...
```

---

## 6. WORKSPACE APIs & STRUCTURED ERRORS

The frontend requires comprehensive Workspace APIs to manage state.

### APIs Defined
* `GET /projects` - Get User Projects
* `GET /posts` - Get Generated Posts
* `GET /schedule` - Get Scheduled Posts
* `DELETE /posts/:id` - Soft Delete Post

### Structured Frontend Errors
FastAPI strictly returns standardized error shapes for excellent UX when AI fails.
```json
{
  "code": "AI_TIMEOUT",
  "message": "Generation took too long. Please try a shorter project description."
}
```

---

## 7. RELIABILITY & OBSERVABILITY

### A. Rate Limiting Strategy
Students will spam generation. We apply per-user limits using `slowapi` in FastAPI.
* Free: 5 generations/day
* Premium: Unlimited

### B. Retry Strategy Definition
If a post fails to publish, APScheduler reschedules it based on this exact backoff:
1. First failure -> Retry after 1 min
2. Second failure -> Retry after 5 min
3. Third failure -> Retry after 15 min
4. Max Retries: 3. Then marked `failed`.

### C. Observability
Implementation of **Structured JSON Logging** (`structlog`) to explicitly track:
* Generation Failures
* LinkedIn Publish Failures
* APScheduler execution misses
* OAuth token expirations

---

## 8. DEPLOYMENT ARCHITECTURE (MVP)

* **Frontend**: Vercel (Next.js)
* **Backend**: Render or Railway (FastAPI)
* **Database**: MongoDB Atlas
* **Background Tasks**: Runs seamlessly inside the FastAPI container using `APScheduler`. No extra Redis cache or separate Celery worker dynos are required for MVP, drastically cutting operational costs.

*(Note: Even instant generation is ideally an async background job that the frontend polls. For MVP v1, running instant generation inside the HTTP request cycle is acceptable, provided timeout safeguards exist).*
