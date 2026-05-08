# Social Media Automation Platform - Backend

A production-style social media automation system built with FastAPI, MongoDB, and APScheduler.

**Status**: MVP (Minimum Viable Product) - LinkedIn posting automation ready for development.

---

## Quick Start (5 minutes)

### Prerequisites
- Python 3.9+
- MongoDB Atlas account (free tier available)
- LinkedIn app credentials (for OAuth)

### 1. Setup Environment

```bash
# Clone/enter backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Create Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env with your values (see section below)
# Important: Never commit .env to git!
```

### 3. Setup MongoDB Atlas

1. Create free account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster (M0)
3. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/social_automation?retryWrites=true&w=majority`
4. Add to `.env` as `MONGODB_URL`

### 4. Setup LinkedIn OAuth

1. Go to https://www.linkedin.com/developers/apps
2. Create new app (requires LinkedIn company page)
3. In app settings, add Authorized redirect URLs: `http://localhost:8000/auth/callback`
4. Copy Client ID and Client Secret to `.env`

### 5. Run Backend

```bash
# Start development server
python -m uvicorn app.main:app --reload

# Server runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Environment Variables (.env)

```env
# MongoDB
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/social_automation?retryWrites=true&w=majority
MONGODB_DB_NAME=social_automation

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your_secret_key_here

# App Settings
APP_ENV=development
DEBUG=True
```

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py          # All API endpoints
│   ├── services/
│   │   ├── auth_service.py    # OAuth & JWT
│   │   └── post_service.py    # Post CRUD & validation
│   ├── scheduler/
│   │   └── scheduler.py       # APScheduler jobs
│   ├── models/
│   │   └── schemas.py         # Pydantic models + database schemas
│   ├── db/
│   │   └── mongodb.py         # MongoDB connection
│   ├── utils/
│   │   ├── config.py          # Settings management
│   │   └── logger.py          # Logging setup
│   └── main.py                # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
└── Dockerfile                 # Docker configuration
```

---

## API Endpoints

### Public
- `GET /health` - Health check
- `GET /auth/linkedin/url` - Get LinkedIn login URL
- `GET /auth/callback?code=...` - OAuth callback

### Protected (Require JWT Token)
- `POST /api/posts` - Create scheduled post
- `GET /api/posts` - List user's posts
- `GET /api/posts/{id}` - Get post details
- `PUT /api/posts/{id}` - Update post
- `DELETE /api/posts/{id}` - Delete post
- `GET /api/me` - Get current user

**Authentication**: Include JWT token in header:
```
Authorization: Bearer your_jwt_token_here
```

---

## Interactive API Documentation

Visit http://localhost:8000/docs (Swagger UI)
- Try all endpoints without writing code
- See request/response schemas
- Auto-generated from Pydantic models

---

## How Things Work

### 1. Authentication Flow

```
User clicks "Login with LinkedIn"
        ↓
Frontend redirects to /auth/linkedin/url
        ↓
User logs in on LinkedIn
        ↓
LinkedIn redirects to /auth/callback?code=...
        ↓
Backend exchanges code for access token
        ↓
Backend creates user in MongoDB
        ↓
Backend generates JWT token
        ↓
Frontend receives JWT token
        ↓
Frontend stores token (localStorage)
        ↓
Frontend sends token with each API request
```

### 2. Post Scheduling

```
User creates scheduled post for 10 AM tomorrow
        ↓
Backend validates content + time
        ↓
Backend saves post to MongoDB
        ↓
APScheduler registers job
        ↓
At 10 AM, APScheduler triggers publish_post_job()
        ↓
Job fetches post from MongoDB
        ↓
Job gets user's LinkedIn credentials
        ↓
Job calls LinkedIn API to publish
        ↓
Job updates post status to "posted"
        ↓
If error: retry with exponential backoff (5s, 25s, 125s)
        ↓
After 3 failed attempts: mark as "failed" + notify user
```

### 3. Retry Logic

**Exponential Backoff**: Each retry waits longer
- Attempt 1: Fails immediately
- Attempt 2: Wait 5 seconds, retry
- Attempt 3: Wait 25 seconds, retry
- Attempt 4: Wait 125 seconds, retry
- Attempt 5+: Give up, mark as failed

**Why?**
- Handles temporary API outages gracefully
- Doesn't hammer LinkedIn API
- Increases success rate dramatically
- Industry-standard pattern (used by AWS, Google, etc.)

---

## Logging

Logs stored in `logs/` directory with daily rotation.

**Log Levels**:
- `DEBUG`: Detailed information for development
- `INFO`: General information about operations
- `WARNING`: Something unexpected but not critical
- `ERROR`: Something failed
- `CRITICAL`: System won't continue

**View logs**:
```bash
# Recent logs
tail -f logs/app_*.log

# Search for errors
grep ERROR logs/app_*.log

# View from JSON formatter
# Logs are stored as JSON for easy parsing
```

---

## Running Tests (Future)

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=app
```

---

## Development Tips

### 1. Use Interactive Docs
- Go to http://localhost:8000/docs
- Try API endpoints without writing frontend code
- Useful for testing while developing

### 2. Check Database
```bash
# Connect to MongoDB in terminal (after installing mongosh)
mongosh "mongodb+srv://username:password@cluster.mongodb.net/social_automation"

# View collections
db.users.find()
db.posts.find()
```

### 3. Monitor Logs
```bash
# Watch logs in real-time
tail -f logs/app_*.log
```

### 4. Reload on Changes
The `--reload` flag auto-restarts server on code changes. Perfect for development.

---

## Common Issues & Solutions

### ❌ MongoDB Connection Failed
**Problem**: `ServerSelectionTimeoutError`
- Check MongoDB URL in `.env`
- Verify MongoDB Atlas IP whitelist allows your machine
- Try connecting with mongosh first

### ❌ LinkedIn OAuth Errors
**Problem**: `Invalid redirect_uri`
- Registered redirect URI must exactly match `.env` value
- LinkedIn app settings → Authorized redirect URLs

### ❌ JWT Token Validation Failed
**Problem**: `Invalid or expired token`
- Token expires after 24 hours (configurable in `.env`)
- User needs to login again to get new token
- Or implement refresh token endpoint (Phase 2)

### ❌ Posts Not Auto-posting
**Problem**: Job doesn't trigger at scheduled time
- Check scheduler logs for errors
- Verify server is still running (scheduler needs to stay running)
- MongoDB post status should be "scheduled"
- Scheduled time should be in future

---

## Next Steps

### Phase 2: LinkedIn Integration
- Implement real LinkedIn API calls
- Handle LinkedIn error responses
- Test posting with real LinkedIn account

### Phase 3: Frontend Dashboard
- Build Next.js dashboard
- Login/logout flow
- Create post form
- View scheduled posts

### Phase 4: Production Deployment
- Docker containerization
- Deploy to Railway or Render
- Setup monitoring + alerting

---

## Architecture Decisions Explained

**Why FastAPI?**
- Fast async framework (built on Starlette)
- Auto-generated API documentation
- Built-in data validation (Pydantic)
- Easy to understand (like Flask but better)

**Why MongoDB?**
- You already know it
- Flexible schema (easy to evolve)
- Good async support (Motor)
- Free tier on MongoDB Atlas

**Why APScheduler?**
- Simple for MVP
- In-memory job storage (sufficient for single machine)
- Easy to understand
- Can upgrade to Celery later if needed

**Why Modular Services?**
- Each service has ONE responsibility
- Easy to test independently
- Reusable across endpoints
- Industry-standard pattern

---

## Production Considerations

These are things to add AFTER MVP works:

1. **Persistent Job Store**: Save jobs to database (survive restarts)
2. **Job Queue**: Use Redis + Celery (handle thousands of jobs)
3. **Rate Limiting**: Prevent abuse
4. **Database Migrations**: Track schema changes
5. **Monitoring**: Errors, performance, uptime
6. **Backups**: MongoDB Atlas automatic backups
7. **Caching**: Redis for frequently accessed data
8. **API Rate Limits**: Per-user limits
9. **Webhook Verification**: Secure callbacks from LinkedIn
10. **Secrets Management**: Use Vault or AWS Secrets Manager

---

## Support & Questions

- FastAPI docs: https://fastapi.tiangolo.com/
- MongoDB async: https://motor.readthedocs.io/
- APScheduler: https://apscheduler.readthedocs.io/
- LinkedIn API: https://docs.microsoft.com/en-us/linkedin/

---

## License

Private project for learning.
