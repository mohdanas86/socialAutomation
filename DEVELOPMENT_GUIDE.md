# Development Guide - Step-by-Step Setup

This guide walks through setting up your development environment and understanding how everything works together.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [MongoDB Atlas Setup](#mongodb-atlas-setup)
3. [LinkedIn OAuth Setup](#linkedin-oauth-setup)
4. [Backend Environment Setup](#backend-environment-setup)
5. [Understanding the Architecture](#understanding-the-architecture)
6. [First Run](#first-run)
7. [Common Development Tasks](#common-development-tasks)

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.9+** - Download from https://www.python.org/
  - Verify: `python --version`
- **Git** - For version control
- **GitHub Account** - For hosting code
- **MongoDB Atlas Account** - Free tier available
- **LinkedIn Account** - For OAuth testing

---

## MongoDB Atlas Setup

### Step 1: Create MongoDB Atlas Account

1. Go to https://www.mongodb.com/cloud/atlas
2. Click "Sign Up"
3. Create account (use your email)
4. Verify email

### Step 2: Create a Free Cluster

1. After login, click "Create a Deployment"
2. Choose "M0 (Free Tier)"
3. Select provider: AWS, GCP, or Azure (doesn't matter)
4. Select region closest to you
5. Click "Create Deployment"
6. Wait 1-3 minutes for cluster to initialize

### Step 3: Setup Database User

1. In MongoDB Atlas dashboard, go to "Database Access"
2. Click "Add New Database User"
3. Choose "Username and Password" authentication
4. Username: `dev` (or any name)
5. Password: Generate a strong password (copy it!)
6. Click "Add User"

### Step 4: Allow Network Access

1. Go to "Network Access"
2. Click "Add IP Address"
3. Choose "Allow access from anywhere" (for development only!)
4. In production: Only allow your server IP

### Step 5: Get Connection String

1. Go back to "Database"
2. Click "Connect" on your cluster
3. Choose "Drivers"
4. Language: Python
5. Driver: PyMongo 3.12 or later
6. Copy the connection string
7. Replace `<password>` with your user password
8. Replace `<username>` with your username

**Example**:
```
mongodb+srv://dev:mypassword123@cluster.mongodb.net/social_automation?retryWrites=true&w=majority
```

### Step 6: Create Database

By default, the database doesn't exist until you write to it. FastAPI does this automatically when:
1. App starts
2. First user signs up (users collection created)
3. First post is scheduled (posts collection created)

---

## LinkedIn OAuth Setup

### Step 1: Create LinkedIn App

1. Go to https://www.linkedin.com/developers/apps
2. Click "Create app"
3. Choose a LinkedIn Page (you need one - create one first if needed)
4. Fill in:
   - **App name**: "Social Automation MVP"
   - **LinkedIn Page**: Your company page
   - **Legal agreement**: Check boxes
5. Click "Create app"

### Step 2: Get Credentials

In the app dashboard:
1. Go to "Auth" tab
2. Copy **Client ID**
3. Copy **Client Secret** (keep this SECRET!)
4. Click "Generate" for authorization token if needed

### Step 3: Add Authorized Redirect URI

1. Still in "Auth" tab
2. Under "Authorized redirect URLs"
3. Click "Add redirect URL"
4. Add: `http://localhost:8000/auth/callback` (for local development)
5. Save

### Step 4: Request Access (Important!)

LinkedIn API access requires approval from LinkedIn:
1. Go to "Products" tab in your app
2. Request access to:
   - **Sign In with LinkedIn** (to login users)
   - **Share on LinkedIn** (to post)
3. LinkedIn reviews (usually 24-48 hours)

**Note**: Sign In with LinkedIn is usually approved quickly. Share on LinkedIn might take longer or require additional documentation.

---

## Backend Environment Setup

### Step 1: Clone/Navigate to Backend

```bash
cd backend
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages:
- `fastapi` - Web framework
- `motor` - Async MongoDB driver
- `apscheduler` - Job scheduling
- `python-jose` - JWT tokens
- `authlib` - OAuth2
- etc.

### Step 4: Generate JWT Secret

You need a random secret for JWT tokens:

```bash
# Generate and copy the output
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Create .env File

Copy and edit:

```bash
cp .env.example .env
```

Then edit `.env` with your values:

```env
# MongoDB connection string from Atlas
MONGODB_URL=mongodb+srv://dev:yourpassword@cluster.mongodb.net/social_automation?retryWrites=true&w=majority
MONGODB_DB_NAME=social_automation

# LinkedIn OAuth credentials
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT (paste the generated secret)
JWT_SECRET_KEY=your_random_secret_here

# Optional (defaults shown)
APP_ENV=development
DEBUG=True
API_HOST=0.0.0.0
API_PORT=8000
```

### Step 6: Test MongoDB Connection

```bash
python -c "
from app.db.mongodb import connect_to_mongo
import asyncio
asyncio.run(connect_to_mongo())
print('✅ Connected to MongoDB!')
"
```

If you see errors:
- Check your connection string
- Verify IP whitelist in MongoDB Atlas
- Ensure network access is "Allow from Anywhere"

---

## Understanding the Architecture

### File Purpose Map

```
app/
├── main.py
│   └── WHY: Entry point, initializes FastAPI
│       - Creates app instance
│       - Registers all routes
│       - Handles startup/shutdown
│       - Sets up error handling
│
├── api/routes.py
│   └── WHY: All HTTP endpoints
│       - Receives requests from clients
│       - Delegates to services
│       - Returns responses
│       - Validates authentication
│
├── services/
│   ├── auth_service.py
│   │   └── WHY: Authentication logic
│   │       - OAuth2 flow
│   │       - JWT token creation/validation
│   │       - User management
│   │
│   └── post_service.py
│       └── WHY: Post business logic
│           - CRUD operations
│           - Validation
│           - Status tracking
│
├── scheduler/scheduler.py
│   └── WHY: Background jobs
│       - Manages APScheduler
│       - Registers post publishing jobs
│       - Implements retry logic
│
├── db/mongodb.py
│   └── WHY: Database connection
│       - Connection pooling
│       - Async queries
│       - Index creation
│
├── models/schemas.py
│   └── WHY: Data validation
│       - Pydantic request/response models
│       - MongoDB document schemas
│       - Type hints
│
└── utils/
    ├── config.py
    │   └── WHY: Environment variables
    │       - Centralized settings
    │       - Validation
    │
    └── logger.py
        └── WHY: Structured logging
            - JSON format for parsing
            - File + console output
```

### Data Flow Diagrams

**Creating a Scheduled Post:**
```
Browser
  ↓ POST /api/posts
FastAPI Routes
  ↓ Validate request (Pydantic)
Authentication
  ↓ Verify JWT token
Post Service
  ↓ Validate content, check time
Database (MongoDB)
  ↓ Insert post document
Scheduler
  ↓ Register job for scheduled time
Response
  ↓ Return post ID to browser
```

**Publishing a Scheduled Post:**
```
Scheduled Time Arrives
  ↓
APScheduler
  ↓ Call publish_post_job(post_id)
Post Service
  ↓ Fetch post from DB
Auth Service
  ↓ Get user's LinkedIn token
LinkedIn API
  ↓ POST /posts (publish)
LinkedIn
  ↓ Return post ID
Post Service
  ↓ Update post status = "posted"
Database
  ↓ Save post status
Success ✅
```

**On Failure (Retry Loop):**
```
Publishing Fails
  ↓
Catch Exception
  ↓ Increment retry_count
  ↓ Calculate wait time: 5^(attempt)
  ↓ Sleep(wait_time)
  ↓ Try again
  ↓
If retry_count >= 3:
  ↓ Mark post as "failed"
  ↓ Save error message
  ↓ Notify user via API
```

---

## First Run

### Step 1: Start the Server

```bash
# Ensure venv is activated
python -m uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [1234]
```

### Step 2: Check Health

Visit http://localhost:8000/health

You should see:
```json
{
  "status": "healthy",
  "environment": "development",
  "timestamp": "2026-05-08T10:00:00"
}
```

### Step 3: View API Documentation

Visit http://localhost:8000/docs

You should see an interactive Swagger UI with all endpoints listed.

### Step 4: Test Endpoints (Optional)

In the Swagger UI, you can test endpoints. For now, only `/health` works without authentication.

---

## Common Development Tasks

### Task 1: Debug a Specific Function

```python
# In your code, add breakpoint
async def create_post(...):
    breakpoint()  # Pauses execution here
    ...
```

Run without `--reload`:
```bash
python -m uvicorn app.main:app
```

The debugger prompt appears in terminal.

### Task 2: Check MongoDB Data

```bash
# Install MongoDB shell
# Windows: Download mongosh from https://www.mongodb.com/try/download/shell
# Mac: brew install mongosh

# Connect
mongosh "mongodb+srv://dev:password@cluster.mongodb.net/social_automation"

# View collections
show databases
show collections

# Query data
db.users.find()
db.posts.find()
db.posts.findOne({status: "failed"})

# Count documents
db.posts.countDocuments({status: "scheduled"})
```

### Task 3: Check Logs

```bash
# Real-time log viewing
tail -f logs/app_*.log

# Search for errors
grep ERROR logs/app_*.log

# Count by level
grep -c INFO logs/app_*.log
```

### Task 4: Reset Everything

If you want to start fresh:

```bash
# Delete local logs
rm logs/*

# Delete MongoDB data (via MongoDB Atlas dashboard):
# 1. Go to Clusters
# 2. Click Collections
# 3. Select social_automation database
# 4. Delete collections (users, posts)

# Remove local .env if you want
rm .env
cp .env.example .env

# Recreate virtual environment
rm -r venv
python -m venv venv
venv\Scripts\activate  # or source venv/bin/activate
pip install -r requirements.txt
```

### Task 5: Make Code Changes

The `--reload` flag watches files for changes and restarts server automatically:

1. Make code change
2. Save file
3. Check terminal - should show "Restarting..."
4. Refresh browser or retry request
5. See changes immediately

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

**Problem**: Python can't find your app
**Solution**: 
- Ensure you're in `backend/` directory
- Ensure venv is activated (see `(venv)` in terminal)
- Reinstall: `pip install -e .`

### "Connection refused" - Can't connect to MongoDB

**Problem**: MongoDB connection failing
**Solution**:
- Check MongoDB URL in `.env`
- Try connecting with mongosh first
- Check IP whitelist in MongoDB Atlas (should be "Allow from Anywhere")
- Check network connectivity
- Restart MongoDB Atlas cluster

### "Invalid client credentials" - OAuth failing

**Problem**: LinkedIn OAuth errors
**Solution**:
- Check `LINKEDIN_CLIENT_ID` in `.env`
- Check `LINKEDIN_CLIENT_SECRET` in `.env`
- Verify redirect URI matches exactly: `http://localhost:8000/auth/callback`
- Request app access from LinkedIn

### Port 8000 Already in Use

**Problem**: `Address already in use: ('0.0.0.0', 8000)`
**Solution**:
```bash
# Option 1: Use different port
python -m uvicorn app.main:app --port 8001

# Option 2: Kill process using port
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Mac/Linux
lsof -i :8000
kill -9 <pid>
```

---

## Next: Building LinkedIn Integration

Now that your backend is set up, the next step is:

1. Implement real LinkedIn OAuth flow in `/auth/callback`
2. Test user login
3. Implement LinkedIn post publishing
4. Test end-to-end post scheduling

See `ARCHITECTURE.md` for detailed explanations of each component.

---

## Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **MongoDB Atlas**: https://docs.atlas.mongodb.com/
- **Motor (Async MongoDB)**: https://motor.readthedocs.io/
- **APScheduler**: https://apscheduler.readthedocs.io/
- **LinkedIn API**: https://docs.microsoft.com/en-us/linkedin/
- **JWT Tokens**: https://jwt.io/

