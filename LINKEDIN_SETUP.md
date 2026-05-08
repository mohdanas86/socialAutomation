# LinkedIn OAuth Setup - Step by Step

## ⚠️ REQUIRED BEFORE RUNNING

Your app won't work with placeholder credentials! You must complete these steps first.

---

## Step 1: Create LinkedIn Developer App

1. Go to https://www.linkedin.com/developers/apps
2. Click **"Create app"**
3. Fill in the form:
   - **App name**: Social Automation MVP
   - **LinkedIn Page**: (Select your company page, or create one first)
   - **Legal agreement**: Check the boxes
4. Click **"Create app"**
5. You're now in the app dashboard

---

## Step 2: Get Your Credentials

In the app dashboard:

1. Go to **"Auth"** tab
2. Copy your **Client ID** (save it)
3. Copy your **Client Secret** (SAVE SECURELY!)

**These values go in your .env file:**
```env
LINKEDIN_CLIENT_ID=<your_client_id>
LINKEDIN_CLIENT_SECRET=<your_client_secret>
```

---

## Step 3: Add Authorized Redirect URI

Still in the **"Auth"** tab:

1. Scroll to **"Authorized redirect URLs"**
2. Click **"Add redirect URL"**
3. Enter: `http://localhost:8000/auth/callback`
4. Click **"Add"**
5. Save your app

(In production, you'll add your production domain here too)

---

## Step 4: Request API Access

Your app needs permission to:
- Sign in with LinkedIn (usually approved quickly)
- Share posts (may require additional review)

To request:

1. Go to **"Products"** tab
2. Look for:
   - **Sign In with LinkedIn** (likely already approved)
   - **Share on LinkedIn** (might need to request)
3. Click **"Request access"** for any that show "Not approved"
4. LinkedIn reviews (usually 24-48 hours)

---

## Step 5: Generate JWT Secret

In terminal:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output. This goes in .env:
```env
JWT_SECRET_KEY=<the_generated_secret>
```

---

## Step 6: Update .env File

Edit `backend/.env` and fill in:

```env
LINKEDIN_CLIENT_ID=<your_client_id_from_step_2>
LINKEDIN_CLIENT_SECRET=<your_client_secret_from_step_2>
JWT_SECRET_KEY=<generated_secret_from_step_5>
```

Keep everything else as-is.

---

## Step 7: Verify Configuration

Check if all required variables are filled:

```bash
cd backend
python -c "from app.utils.config import settings; print('✅ Config valid!' if settings.linkedin_client_id != 'your_client_id_here' else '❌ Still has placeholder values')"
```

If you see ✅, you're ready!

---

## Testing the OAuth Flow

Once you have real credentials:

```bash
# Terminal 1: Start backend
cd backend
python -m uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd front
npm run dev

# Browser: Open http://localhost:3000
# Click "Login with LinkedIn"
# You should be redirected to LinkedIn
# After approval, redirected back to dashboard
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic_settings'"
```bash
cd backend
pip install -r requirements.txt
```

### "LinkedIn OAuth URL generation failed"
- Check that `LINKEDIN_CLIENT_ID` is NOT still "your_client_id_here"
- Run: `python -m uvicorn app.main:app --reload` (without `--no-reload`)
- Check console for validation errors

### "Invalid client credentials" error from LinkedIn
- Double-check `LINKEDIN_CLIENT_SECRET` is exactly correct
- Ensure no extra spaces or quotes in .env

### "Redirect URI mismatch"
- Your .env has: `LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/callback`
- You registered in LinkedIn app: `http://localhost:8000/auth/callback`
- These MUST match exactly (including http vs https)

### "Not approved for API access"
- You haven't requested access to "Sign In with LinkedIn" or "Share on LinkedIn"
- Go to LinkedIn Developer Dashboard → Products → Request access
- Wait for LinkedIn approval (usually quick for Sign In)

---

## What Happens During Login

1. User clicks "Login with LinkedIn"
2. Frontend calls `GET /auth/linkedin/url`
3. Backend returns LinkedIn's OAuth URL
4. Frontend redirects user to LinkedIn
5. User logs in & approves permissions
6. LinkedIn redirects to `http://localhost:8000/auth/callback?code=...`
7. Backend exchanges code for access token
8. Backend fetches user profile & email
9. Backend creates JWT token
10. Backend redirects to `http://localhost:3000/dashboard?token=...`
11. Frontend stores token & shows dashboard

---

## Environment Variables Reference

| Variable                 | Example                               | Notes                                 |
| ------------------------ | ------------------------------------- | ------------------------------------- |
| `LINKEDIN_CLIENT_ID`     | `12345abcde`                          | From LinkedIn Developer Dashboard     |
| `LINKEDIN_CLIENT_SECRET` | `secret_xyz`                          | Keep this SECRET! Never commit to git |
| `LINKEDIN_REDIRECT_URI`  | `http://localhost:8000/auth/callback` | Must match LinkedIn app settings      |
| `JWT_SECRET_KEY`         | `random_secret_123...`                | Generate with `secrets` module        |
| `MONGODB_URL`            | `mongodb+srv://user:pass@...`         | Your MongoDB Atlas connection string  |
| `MONGODB_DB_NAME`        | `social_automation`                   | Name of your database                 |

---

## Next Steps

1. ✅ Create LinkedIn app & get credentials
2. ✅ Update .env file
3. ⏭️ Start backend & frontend
4. ⏭️ Test OAuth login
5. ⏭️ Test creating & scheduling posts
