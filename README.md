# Quick Start Guide - Social Media Automation Platform

Welcome! This is your production-style social media automation system. Let's get you up and running.

---

## 📋 What We've Built So Far

✅ **Backend Architecture**
- FastAPI web server with async support
- MongoDB integration (async driver - Motor)
- APScheduler for background jobs
- Modular service layer (clean architecture)
- Comprehensive logging
- Environment configuration management

✅ **Database Design**
- Users collection (OAuth, credentials)
- Posts collection (scheduling, tracking)
- Indexes for performance

✅ **API Endpoints** (ready for implementation)
- Authentication (OAuth2, JWT)
- Post CRUD operations
- User management

✅ **Job Scheduling**
- APScheduler setup
- Exponential backoff retry logic
- Post publishing pipeline

✅ **Production-Grade Features**
- Error handling with retries
- Structured JSON logging
- Type hints throughout
- Modular, testable code

---

## 🚀 Getting Started (Choose Your Path)

### Path A: Quick 5-Minute Setup (Recommended for First-Time)

```bash
# 1. Go to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env (see section below)

# 6. Start server
python -m uvicorn app.main:app --reload

# 7. Visit http://localhost:8000/docs
```

### Path B: Detailed Setup with Explanations

👉 **Go to [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)**
- Step-by-step MongoDB Atlas setup
- LinkedIn OAuth configuration
- Detailed troubleshooting
- Architecture explanations

---

## 🔧 Configure Environment Variables

Create `backend/.env` file:

```env
# MONGODB ATLAS (https://www.mongodb.com/cloud/atlas)
# Get connection string from: Connect → Drivers → Python
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/social_automation?retryWrites=true&w=majority
MONGODB_DB_NAME=social_automation

# LINKEDIN OAUTH (https://www.linkedin.com/developers/apps)
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT SECRET (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your_generated_secret_here

# OPTIONAL (defaults provided)
APP_ENV=development
DEBUG=True
```

---

## 📚 What's Where?

| File/Folder                                  | Purpose                                  |
| -------------------------------------------- | ---------------------------------------- |
| [ARCHITECTURE.md](ARCHITECTURE.md)           | System design, WHY decisions, workflows  |
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Step-by-step setup, MongoDB/OAuth config |
| [backend/README.md](backend/README.md)       | Backend documentation, API reference     |
| `backend/app/main.py`                        | FastAPI app entry point                  |
| `backend/app/api/routes.py`                  | All HTTP endpoints                       |
| `backend/app/services/`                      | Business logic (auth, posts)             |
| `backend/app/scheduler/`                     | Background job scheduling                |
| `backend/app/db/`                            | MongoDB connection                       |
| `backend/app/models/`                        | Data validation (Pydantic)               |
| `backend/app/utils/`                         | Config, logging                          |

---

## ✅ Verification Checklist

After setup, verify everything works:

```bash
# 1. Virtual environment activated?
# Should see (venv) in terminal prompt

# 2. Dependencies installed?
pip list | grep -E "fastapi|motor|apscheduler"

# 3. .env file created with values?
cat backend/.env

# 4. Start server
python -m uvicorn app.main:app --reload

# 5. Health check
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}

# 6. API documentation
# Open http://localhost:8000/docs in browser
# Should see Swagger UI with all endpoints
```

---

## 🎯 Phase 1: MVP Planning

### What We're Building Next

**Phase 1A: Implement OAuth2 Callback** (This Week)
- Receive authorization code from LinkedIn
- Exchange code for access token
- Create/update user in MongoDB
- Return JWT token to frontend
- Status: 🔄 Skeleton exists, needs implementation

**Phase 1B: Build Frontend Dashboard** (Next Week)
- Next.js app on http://localhost:3000
- Login page (redirects to LinkedIn OAuth)
- Create post form
- List scheduled posts
- Status: ⏳ Not started

**Phase 1C: LinkedIn API Integration** (After Frontend)
- Call LinkedIn API to publish posts
- Handle LinkedIn errors/rate limits
- Test with real LinkedIn account
- Status: ⏳ Skeleton exists, needs implementation

**Phase 1D: Deploy & Polish** (Final Week)
- Docker containerization
- Deploy to Railway/Render
- Add tests
- Status: ⏳ Not started

---

## 💡 How to Use This System

### For Learning
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand WHY things are designed this way
2. Look at code comments explaining each module
3. Try modifying things - the `--reload` flag makes development fast
4. Check logs in `backend/logs/` to see what's happening

### For Development
1. API docs at http://localhost:8000/docs (interactive testing)
2. Change code → auto-reloads → refresh browser → see changes
3. Check logs for debugging: `tail -f backend/logs/app_*.log`
4. MongoDB data at MongoDB Atlas dashboard

### For Production
- Later we'll use Docker and deploy to Railway/Render
- For now: local development only

---

## 🔍 Understanding the Code Flow

### Example: Creating a Scheduled Post

```python
# User submits form on frontend
# POST /api/posts
# {
#   "content": "My post...",
#   "scheduled_time": "2026-05-09T10:00:00"
# }

# ↓ FastAPI validates with Pydantic (backend/app/models/schemas.py)
# ↓ Routes file checks JWT token (backend/app/api/routes.py)
# ↓ Calls PostService.create_post() (backend/app/services/post_service.py)
# ↓ PostService validates business logic
# ↓ Saves to MongoDB (backend/app/db/mongodb.py)
# ↓ APScheduler registers job (backend/app/scheduler/scheduler.py)
# ↓ Returns success response

# Later, at scheduled time:
# ↓ APScheduler triggers publish_post_job()
# ↓ Fetches post from MongoDB
# ↓ Gets user's LinkedIn credentials
# ↓ Calls LinkedIn API to publish
# ↓ Updates post status to "posted"
# ↓ If fails, retries with exponential backoff
```

---

## 🛠️ Common Development Commands

```bash
# Install a new package
pip install package_name
pip freeze > requirements.txt

# Run tests (when we add them)
pytest

# Check code quality
pylint app/
mypy app/  # Type checking

# Format code
black app/

# View running processes
ps aux | grep uvicorn

# Kill server (if needed)
Ctrl+C
```

---

## 📞 Getting Help

### If Something Breaks

1. **Check logs**: `tail -f backend/logs/app_*.log`
2. **Read error message carefully**: Usually explains the problem
3. **Try the obvious**: Restart server, refresh browser
4. **Check DEVELOPMENT_GUIDE.md**: Has troubleshooting section
5. **Google the error**: Most errors have solutions online

### Questions About Design

👉 See [ARCHITECTURE.md](ARCHITECTURE.md) - explains WHY each decision was made

### Questions About Implementation

👉 Code comments explain the HOW

### Questions About Setup

👉 See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)

---

## 🎓 What You'll Learn

By building this system, you'll understand:

✅ **Async Programming**: Non-blocking I/O, event loops
✅ **Job Scheduling**: Background tasks, cron jobs, retries
✅ **OAuth2**: Third-party authentication (LinkedIn, Google, etc.)
✅ **Database Design**: MongoDB collections, indexing, queries
✅ **REST APIs**: Request/response patterns, status codes, error handling
✅ **Error Handling**: Retries, exponential backoff, graceful degradation
✅ **Logging**: Structured logs, debugging production systems
✅ **Architecture**: Modular design, service layer, clean code
✅ **Deployment**: Docker, environment variables, secrets management
✅ **Type Hints**: Making code self-documenting and safer

This is real production engineering. Congrats on learning it! 🎉

---

## 📖 Next Step

**Ready to build?**

1. If you're new: Start with [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
2. If you understand the setup: Jump to implementation

**After setup is complete:**
1. We'll implement LinkedIn OAuth flow
2. Build Next.js frontend
3. Test end-to-end posting
4. Deploy to production

---

## 📞 Contact & Questions

This project is designed as a learning tool. Each file has detailed comments explaining:
- WHY it exists
- WHAT it does
- HOW it works

Before asking questions, check:
1. Code comments in the relevant file
2. ARCHITECTURE.md for system design
3. DEVELOPMENT_GUIDE.md for setup issues
4. Logs in backend/logs/ for runtime issues

---

## 🎯 Success Criteria

After Phase 1, you'll have:
- ✅ Understanding of production backend architecture
- ✅ Working OAuth2 integration
- ✅ Database with users and scheduled posts
- ✅ APScheduler posting jobs
- ✅ Error handling and retries
- ✅ Comprehensive logging
- ✅ Deployable Docker container

This is a real project you can show employers. Great work getting here! 🚀

