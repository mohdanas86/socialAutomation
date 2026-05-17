# AI Career Visibility Platform — System Design Document (MVP v1 & Beyond)

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
 ├── Project Analyzer
 ├── AI Generation Service (Gemini/OpenRouter)
 ├── Scheduling Service (APScheduler)
 ├── Platform Services (LinkedIn Service, Insta Service...)
        ↓
MongoDB (Async via Motor)
```

**Key Senior SDE Decisions vs Traditional Boilerplate:**
* **No Celery/Redis for MVP**: We use **APScheduler** for in-memory, reliable background task scheduling with exponential backoff. This drastically reduces infrastructure complexity, cost, and moving parts.
* **No PostgreSQL**: We use **MongoDB**. Social media APIs frequently change their payload structures, and different platforms (LinkedIn vs Instagram) require storing different token shapes and profile data. MongoDB's schema flexibility is perfect for this.
* **Decoupled Auth**: We separate the *User Account* from the *Social Connection*. A user creates an account first, then explicitly "Connects" platforms.

---

## 3. HIGH LEVEL FLOWS

### FLOW A — Onboarding & Platform Connection
```text
User Signs Up (Email/Password or Primary OAuth)
    ↓
Creates Base User Profile in DB
    ↓
Navigates to "Integrations" Dashboard
    ↓
Connects LinkedIn (OAuth Flow)
    ↓
Stores LinkedIn Access Tokens inside user's `integrations` sub-document
```

### FLOW B — Instant Post
```text
User Input + Selected Platform(s)
    ↓
POST /generation/instant
    ↓
Project Analyzer
    ↓
Content Strategy Selector (Platform-Aware)
    ↓
AI Post Generator
    ↓
Humanizer Layer
    ↓
Publish Instantly via Platform Service(s) (e.g., LinkedInService.publish)
    ↓
Return Post URLs
```

### FLOW C — Scheduled Posts
```text
User Input + Selected Platform(s) + Time
    ↓
POST /generation/schedule
    ↓
Generate Posts
    ↓
Save Posts to DB (Status: Scheduled)
    ↓
APScheduler Registers Job in Memory
    ↓
At Scheduled Time -> Fetch Tokens -> Publish via Platform Service
```

---

## 4. DATABASE DESIGN (MongoDB Schema)

We use MongoDB for flexibility. Data is stored as JSON documents.

### Collection: `users`
```json
{
  "_id": "ObjectId",
  "name": "John Doe",
  "email": "student@university.edu",
  "password_hash": "...", 
  "created_at": "ISODate()",
  "integrations": {
    "linkedin": {
      "linkedin_id": "urn:li:person:123",
      "access_token": "token...",
      "token_expiry": "ISODate()",
      "connected": true
    },
    "instagram": {
      "connected": false
    },
    "github": {
      "connected": false
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
  "github_url": "https://github.com/...",
  "readme_context": "...",
  "problem_solved": "...",
  "tech_stack": ["Next.js", "FastAPI"],
  "created_at": "ISODate()"
}
```

### Collection: `posts`
Combines generated content and scheduling information.
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "project_id": "ObjectId",
  "content": "Excited to share my new project...",
  "platforms": ["linkedin"], 
  "status": "scheduled", // draft, scheduled, posted, failed
  "mode": "schedule", // instant or schedule
  "scheduled_time": "ISODate()",
  "posted_at": null,
  "platform_post_ids": {
    "linkedin": "urn:li:share:123"
  },
  "retry_count": 0,
  "last_error": null,
  "created_at": "ISODate()"
}
```

---

## 5. PROJECT STRUCTURE
```text
/backend
│
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py          # Primary user auth
│   │   ├── integrations.py  # Social connections (LinkedIn OAuth)
│   │   ├── generation.py    # Triggering AI
│   │   ├── posts.py         # CRUD for posts
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── ai/
│   │   │   ├── ai_client.py
│   │   │   ├── project_analyzer.py
│   │   │   ├── post_generator.py
│   │   │   └── humanizer.py
│   │   ├── platforms/
│   │   │   ├── base_platform.py # Interface
│   │   │   ├── linkedin_service.py
│   │   │   ├── instagram_service.py (Future)
│   │   │   └── github_service.py (Future)
│   │
│   ├── scheduler/
│   │   └── scheduler.py     # APScheduler setup & jobs
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── post.py
│   │   └── schemas.py       # Pydantic schemas
│   │
│   ├── db/
│   │   └── mongodb.py
│   │
│   └── utils/
│       ├── prompts.py
│       └── logger.py
│
├── requirements.txt
└── Dockerfile
```

---

## 6. AI GENERATION SYSTEM

DO NOT use one huge prompt.
We use an AI Pipeline architecture.

**STEP 1 — Project Analyzer**
Input: GitHub URL, README, description.
Extracts: Problem, technical depth, achievements, angles.

**STEP 2 — Strategy Engine (Platform-Aware)**
Chooses:
- Tone
- Formatting (LinkedIn needs spacing; Instagram needs visual emojis; GitHub needs technical conciseness)

**STEP 3 — Hook Generator**
Examples: curiosity, achievement, technical insight.

**STEP 4 — Post Generator**
Generates authentic content tailored to the selected platform.

**STEP 5 — Humanizer Layer**
Removes robotic AI phrases ("Delve into", "In today's fast-paced world", "Unlock your potential"). VERY important for student authenticity.

---

## 7. SCHEDULING SYSTEM (APScheduler)

**IMPORTANT**: Scheduling MUST be asynchronous. Do not use `time.sleep()`.

**FLOW**
```text
Generate Posts -> Save to MongoDB -> Register APScheduler Job -> Wait until Scheduled Time -> Publish to Selected Platforms
```

**Job Execution**
```python
async def publish_post_job(post_id: str):
    # 1. Fetch post and user integrations from MongoDB
    # 2. Identify selected target platforms
    # 3. Iterate platforms and call respective platform services
    # 4. Handle retries with exponential backoff directly in the job
```

---

## 8. CONDITIONAL BACKEND LOGIC

**IF `mode = instant`**
ONLY:
* Generate one post.
* Call platform posting service directly in the request context.
* Return post URL/ID to frontend immediately.
* NO scheduling.

**IF `mode = schedule`**
THEN:
* Generate post(s).
* Create schedule in DB.
* Queue jobs in APScheduler.
* Return success schedule confirmation.

---

## 9. SECURITY & BEST PRACTICES

**MUST DO:**
* JWT auth for primary sessions.
* Store OAuth tokens securely in MongoDB (encrypted if possible).
* Rate limiting on AI generation endpoints.
* Sanitize README input to prevent prompt injection.

**DO NOT:**
* Store LinkedIn secrets in the frontend.
* Hardcode giant prompts everywhere (use `utils/prompts.py`).

---

## 10. DEPLOYMENT ARCHITECTURE (MVP)

* **Frontend**: Vercel (Next.js)
* **Backend**: Render or Railway (FastAPI)
* **Database**: MongoDB Atlas
* **Background Tasks**: Runs seamlessly inside the FastAPI container using `APScheduler`. No extra Redis cache or separate Celery worker dynos are required for MVP, drastically cutting operational costs.

---

## 11. FINAL MVP THESIS

You are NOT building:
**Generic LinkedIn automation software.**

You are building:
**Student career visibility infrastructure.**
That positioning guides ALL backend decisions, UI layout, and AI prompt engineering. Every feature must answer: "Does this help a student easily translate their project work into career visibility?"
