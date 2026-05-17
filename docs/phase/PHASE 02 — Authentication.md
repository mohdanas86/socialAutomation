# PHASE 02 — Authentication & User Management

## Phase Goal
Implement complete user registration, login, JWT token management, and authenticated route protection. By end of this phase, users can sign up, log in, get their profile, and all protected routes enforce authentication.

---

## Features Implemented
- User registration with email + password
- Password hashing with bcrypt
- JWT access token generation (HS256)
- Login with email/password → returns JWT
- `/me` endpoint for authenticated user profile
- Auth middleware / dependency injection for protected routes
- Frontend: Registration page, Login page, Auth context/store
- Frontend: Protected route wrapper component
- Logout (client-side token removal)

---

## Technical Architecture

```
app/
├── api/v1/
│   ├── router.py              ← Register auth router here
│   └── routes/
│       └── auth.py            ← /register, /login, /me, /logout
├── services/
│   └── auth_service.py        ← Business logic: register, login, verify
├── repositories/
│   └── user_repository.py     ← (from Phase 01)
├── models/
│   └── user.py                ← Add auth-specific models
├── core/
│   └── security.py            ← JWT creation, verification, password hashing
└── dependencies/
    ├── __init__.py
    └── auth.py                ← get_current_user dependency
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | ❌ Public | Create new user account |
| POST | `/api/v1/auth/login` | ❌ Public | Login → returns JWT |
| GET | `/api/v1/auth/me` | ✅ Protected | Get current user profile |
| POST | `/api/v1/auth/logout` | ✅ Protected | Invalidate session (client-side) |

---

## Request / Response Shapes

### POST `/auth/register`
**Request:**
```json
{
  "name": "Anas Khan",
  "email": "anas@srm.edu",
  "password": "SecurePass123"
}
```
**Response 201:**
```json
{
  "id": "667abc...",
  "name": "Anas Khan",
  "email": "anas@srm.edu",
  "plan": "free",
  "is_active": true,
  "integrations": { "linkedin": { "connected": false } },
  "created_at": "2025-01-01T..."
}
```
**Errors:**
```json
{ "code": "EMAIL_TAKEN", "message": "An account with this email already exists." }
```

### POST `/auth/login`
**Request:**
```json
{
  "email": "anas@srm.edu",
  "password": "SecurePass123"
}
```
**Response 200:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "...", "name": "...", "email": "..." }
}
```
**Errors:**
```json
{ "code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect." }
```

### GET `/auth/me`
**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "id": "667abc...",
  "name": "Anas Khan",
  "email": "anas@srm.edu",
  "plan": "free",
  "integrations": { "linkedin": { "connected": false } },
  "created_at": "..."
}
```

---

## Backend Tasks

### 1. Security Module (`app/core/security.py`)
```python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
```

### 2. Auth Dependency (`app/dependencies/auth.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_repo: UserRepository = Depends(lambda: UserRepository())
) -> dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token."}
        )
    
    user = await user_repo.find_by_id(payload["sub"])
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User no longer exists."}
        )
    
    # CRITICAL: Strip sensitive fields before returning
    user.pop("hashed_password", None)
    user.pop("integrations", None)  # use /me for full profile
    return user
```

### 3. Auth Service (`app/services/auth_service.py`)
```python
from datetime import datetime, timezone
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import AppException
from app.models.user import UserCreate

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def register(self, data: UserCreate) -> dict:
        # Check duplicate email
        existing = await self.user_repo.find_by_email(data.email)
        if existing:
            raise AppException(
                code="EMAIL_TAKEN",
                message="An account with this email already exists.",
                status_code=409
            )
        
        now = datetime.now(timezone.utc)
        user_doc = {
            "name": data.name,
            "email": data.email.lower().strip(),
            "hashed_password": hash_password(data.password),
            "is_verified": False,
            "is_active": True,
            "plan": "free",
            "daily_generation_count": 0,
            "daily_generation_reset_at": now,
            "features": {"scheduler_enabled": True},
            "integrations": {
                "linkedin": {
                    "linkedin_id": None,
                    "access_token": None,
                    "refresh_token": None,
                    "token_expires_at": None,
                    "connected": False,
                    "connected_at": None
                }
            },
            "created_at": now,
            "updated_at": now,
            "deleted": False,
            "deleted_at": None
        }
        
        user_id = await self.user_repo.insert_one(user_doc)
        created_user = await self.user_repo.find_by_id(user_id)
        created_user.pop("hashed_password", None)
        return created_user

    async def login(self, email: str, password: str) -> dict:
        user = await self.user_repo.find_by_email(email.lower().strip())
        
        if not user or not verify_password(password, user.get("hashed_password", "")):
            raise AppException(
                code="INVALID_CREDENTIALS",
                message="Email or password is incorrect.",
                status_code=401
            )
        
        if not user.get("is_active"):
            raise AppException(
                code="ACCOUNT_INACTIVE",
                message="Your account has been deactivated.",
                status_code=403
            )
        
        token = create_access_token({"sub": user["id"]})
        user.pop("hashed_password", None)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "plan": user["plan"]
            }
        }
```

### 4. Auth Router (`app/api/v1/routes/auth.py`)
```python
from fastapi import APIRouter, Depends, status
from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserResponse
from app.dependencies.auth import get_current_user
from app.repositories.user_repository import UserRepository
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: AuthService = Depends(AuthService)):
    return await service.register(data)

@router.post("/login")
async def login(data: LoginRequest, service: AuthService = Depends(AuthService)):
    return await service.login(data.email, data.password)

@router.get("/me")
async def me(
    current_user: dict = Depends(get_current_user),
    user_repo: UserRepository = Depends(lambda: UserRepository())
):
    # Return full profile including integrations
    full_user = await user_repo.find_by_id(current_user["id"])
    full_user.pop("hashed_password", None)
    # Mask LinkedIn token for security
    if "integrations" in full_user:
        linkedin = full_user["integrations"].get("linkedin", {})
        if linkedin.get("access_token"):
            linkedin["access_token"] = "***MASKED***"
    return full_user

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    # JWT is stateless; actual logout happens client-side
    # Future: implement token blacklist with Redis
    return {"message": "Logged out successfully."}
```

### 5. Register Route in Main Router (`app/api/v1/router.py`)
```python
from fastapi import APIRouter
from app.api.v1.routes.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
```

### 6. Update Config with JWT settings
```python
# Add to app/core/config.py Settings class:
ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400  # 24 hours
```

---

## Frontend Tasks

### 1. Auth Store (`src/store/auth.ts`)
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => {
        localStorage.setItem('access_token', token);
        set({ user, token, isAuthenticated: true });
      },
      clearAuth: () => {
        localStorage.removeItem('access_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    { name: 'auth-storage' }
  )
);
```

### 2. Auth API calls (`src/lib/auth-api.ts`)
```typescript
import api from './api';
import type { User } from '@/types';

export const registerUser = async (data: {
  name: string;
  email: string;
  password: string;
}): Promise<User> => {
  const res = await api.post('/auth/register', data);
  return res.data;
};

export const loginUser = async (data: {
  email: string;
  password: string;
}): Promise<{ access_token: string; user: User }> => {
  const res = await api.post('/auth/login', data);
  return res.data;
};

export const getMe = async (): Promise<User> => {
  const res = await api.get('/auth/me');
  return res.data;
};
```

### 3. Register Page (`src/app/(auth)/register/page.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { registerUser } from '@/lib/auth-api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/store/auth';

export default function RegisterPage() {
  const router = useRouter();
  const setAuth = useAuthStore(s => s.setAuth);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const user = await registerUser(form);
      // Auto-login after register by calling login
      router.push('/login?registered=true');
    } catch (err: any) {
      setError(err.response?.data?.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md p-8 space-y-6 border rounded-xl shadow-sm">
        <h1 className="text-2xl font-bold">Create Account</h1>
        <div className="space-y-4">
          <div>
            <Label>Full Name</Label>
            <Input
              value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Anas Khan"
            />
          </div>
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              placeholder="anas@srm.edu"
            />
          </div>
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              placeholder="Min 8 characters"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </Button>
        </div>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account? <a href="/login" className="underline">Sign in</a>
        </p>
      </div>
    </div>
  );
}
```

### 4. Protected Route HOC (`src/components/shared/ProtectedRoute.tsx`)
```tsx
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;
  return <>{children}</>;
}
```

---

## AI Workflow Tasks
None in this phase.

---

## Scheduler / Background Tasks
None in this phase.

---

## Security Considerations
- **Never** store plain text passwords — always `hash_password()`
- **Never** return `hashed_password` in any response — strip at service layer
- **Never** return LinkedIn `access_token` in any response — mask it
- JWT `SECRET_KEY` must be minimum 32 characters, cryptographically random
- JWT tokens expire in 24h — enforce via `exp` claim
- On login failure, return same error for both "wrong email" AND "wrong password" — prevents user enumeration
- Email must be normalized to lowercase before storage and lookup

---

## Environment Variables

```env
# Add to backend .env
SECRET_KEY=your-cryptographically-secure-32-char-key-here
ACCESS_TOKEN_EXPIRE_SECONDS=86400
```

---

## Third-Party Services Required
| Service | Purpose |
|---------|---------|
| `passlib[bcrypt]` | Password hashing |
| `python-jose[cryptography]` | JWT generation/verification |

---

## Implementation Steps (Exact Order)

1. Add `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_SECONDS` to `.env` and `config.py`
2. Create `app/core/security.py`
3. Create `app/dependencies/auth.py`
4. Create `app/services/auth_service.py`
5. Create `app/api/v1/routes/auth.py`
6. Update `app/api/v1/router.py` to include auth router
7. Register `app_exception_handler` in `main.py`
8. Test `/auth/register` via Swagger UI (`localhost:8000/docs`)
9. Test `/auth/login` → copy JWT
10. Test `/auth/me` with `Authorization: Bearer <token>`
11. Create frontend auth store
12. Create Register page, Login page
13. Create `ProtectedRoute` component
14. Test full frontend flow: register → login → `/me` call
15. Commit: `git commit -m "Phase 02: Authentication & user management"`

---

## Testing Strategy

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_register_success():
    with patch("app.services.auth_service.UserRepository") as MockRepo:
        MockRepo.return_value.find_by_email = AsyncMock(return_value=None)
        MockRepo.return_value.insert_one = AsyncMock(return_value="fake_id")
        MockRepo.return_value.find_by_id = AsyncMock(return_value={
            "id": "fake_id", "name": "Test", "email": "test@test.com",
            "plan": "free", "is_active": True, "integrations": {},
            "created_at": "2025-01-01T00:00:00"
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/register", json={
                "name": "Test User", "email": "test@test.com", "password": "password123"
            })
        assert response.status_code == 201

@pytest.mark.asyncio
async def test_register_duplicate_email():
    with patch("app.services.auth_service.UserRepository") as MockRepo:
        MockRepo.return_value.find_by_email = AsyncMock(return_value={"id": "existing"})
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/auth/register", json={
                "name": "Test", "email": "taken@test.com", "password": "password123"
            })
        assert response.status_code == 409
        assert response.json()["code"] == "EMAIL_TAKEN"

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/auth/login", json={
            "email": "notexist@test.com", "password": "wrong"
        })
    assert response.status_code == 401
```

---

## Edge Cases
- Login with correct email but wrong password → 401 (same message as wrong email)
- Login with non-existent email → 401 (same message — no user enumeration)
- JWT with expired `exp` → 401 from `get_current_user`
- JWT tampered (wrong signature) → 401
- Register with email already soft-deleted → treat as available (or block — decide & document)
- Password of exactly 8 chars → valid; 7 chars → 422 validation error

---

## Deliverables / Checklist

- [ ] `app/core/security.py` with hash, verify, create_token, decode_token
- [ ] `app/dependencies/auth.py` with `get_current_user`
- [ ] `app/services/auth_service.py` with register and login
- [ ] `app/api/v1/routes/auth.py` with all 4 endpoints
- [ ] Auth router registered in `api_router`
- [ ] `AppException` handler registered in `main.py`
- [ ] `hashed_password` never in any response — verified
- [ ] `access_token` masked in `/me` response
- [ ] Frontend: Register page functional
- [ ] Frontend: Login page functional
- [ ] Frontend: `ProtectedRoute` component created
- [ ] Frontend: Auth store persists token
- [ ] All auth tests pass

---

## Definition of Completion
A new user can register → login → hit `/me` and get their profile. All wrong-credential attempts return proper error codes. `/me` without token returns 401. `hashed_password` and LinkedIn tokens never appear in any response. Frontend register/login forms work end-to-end.