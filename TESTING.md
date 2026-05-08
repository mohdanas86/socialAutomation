# Manual End-to-End Testing Guide

Complete manual testing procedures for the Social Automation Platform.

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000`
- MongoDB Atlas connection working
- LinkedIn OAuth credentials configured in backend `.env`
- LinkedIn developer app created and approved

## Test Scenario 1: Complete OAuth Login Flow

### Goal
Verify user can login via LinkedIn and get authenticated

### Steps

1. **Start Services**
   ```bash
   # Terminal 1: Backend
   cd backend
   python -m uvicorn app.main:app --reload
   # Expected: Server running on http://localhost:8000
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   # Expected: Server running on http://localhost:3000
   ```

2. **Access Login Page**
   - Open browser: http://localhost:3000
   - Click "Login with LinkedIn"
   - Expected: Redirected to LinkedIn login page

3. **LinkedIn Authentication**
   - Login with your LinkedIn test account
   - Grant app permission
   - Expected: Redirected back to dashboard

4. **Verify Authentication**
   - Should see dashboard with your name
   - Token stored in localStorage:
     ```javascript
     // In browser console
     localStorage.getItem('jwt_token')
     // Should return a JWT token (starts with eyJ)
     ```

### Expected Result
✅ User successfully logged in with JWT token stored

---

## Test Scenario 2: Create and Schedule Post

### Goal
Verify post creation and scheduling works

### Steps

1. **Ensure You're Logged In**
   - Navigate to dashboard
   - If not logged in, complete Test Scenario 1

2. **Create Post**
   - Click "Create Post" or navigate to /dashboard/create
   - Enter content: "Testing LinkedIn automation #automation #tech"
   - Schedule for 2 minutes from now
   - Click "Schedule Post"

3. **Verify in Dashboard**
   - Post appears in "Your Posts" list
   - Status shows "scheduled"
   - Scheduled time displays correctly

4. **Verify in MongoDB**
   ```bash
   # In terminal
   mongosh "mongodb+srv://user:password@cluster.mongodb.net/social_automation"
   
   # In mongosh console
   db.posts.findOne({content: {$regex: "Testing LinkedIn"}})
   
   # Expected output
   {
     "_id": ObjectId("..."),
     "user_id": "...",
     "content": "Testing LinkedIn automation #automation #tech",
     "status": "scheduled",
     "scheduled_time": ISODate("2026-05-08T15:02:00.000Z"),
     "platform": "linkedin",
     "retry_count": 0,
     "created_at": ISODate("...")
   }
   ```

### Expected Result
✅ Post created, scheduled, and stored in database

---

## Test Scenario 3: Auto-Publish Scheduled Post

### Goal
Verify scheduled post publishes automatically

### Steps

1. **Create Post for Near-Future**
   - Follow Test Scenario 2
   - Schedule for exactly 1-2 minutes from now

2. **Watch Backend Logs**
   ```bash
   # In terminal running backend, should see:
   # When post is due:
   # INFO: Starting publish job for post [ID]
   # INFO: Publishing post to LinkedIn (user: [ID])
   # INFO: ✅ Post published successfully: urn:li:share:...
   ```

3. **Check Dashboard**
   - Refresh /dashboard
   - Post status changed to "posted"
   - Posted time shows how long ago

4. **Verify on LinkedIn**
   - Login to your LinkedIn profile
   - Go to your profile/posts
   - Should see the published post

5. **Verify in MongoDB**
   ```bash
   db.posts.findOne({content: {$regex: "Testing LinkedIn"}})
   
   # Expected: status changed to "posted"
   # and linkedin_post_id is set
   {
     "status": "posted",
     "linkedin_post_id": "urn:li:share:1234567890",
     "posted_at": ISODate("2026-05-08T15:02:00.000Z"),
     ...
   }
   ```

### Expected Result
✅ Post published automatically at scheduled time, visible on LinkedIn

---

## Test Scenario 4: Post Validation

### Goal
Verify post content validation works

### Steps

1. **Test Empty Content**
   - Go to /dashboard/create
   - Leave content empty
   - Click "Schedule Post"
   - Expected: Error message: "Post content cannot be empty"

2. **Test Too Short**
   - Enter "Hi" (2 chars)
   - Click "Schedule Post"
   - Expected: Error: "Post content must be at least 5 characters"

3. **Test Too Long**
   - Enter 3001 characters (anything repeated)
   - Expected: Error: "Post content exceeds 3000 character limit"

4. **Test All Caps Spam**
   - Enter: "THIS IS A TEST THIS IS A TEST THIS IS A TEST" (all caps)
   - Expected: Error: "Post appears to be spam (all caps text)"

5. **Test Too Many URLs**
   - Enter: "Check these http://url1.com http://url2.com http://url3.com http://url4.com"
   - Expected: Error: "Post contains too many URLs (max 3)"

6. **Test Valid Post**
   - Enter: "This is a valid post about automation"
   - Schedule for future
   - Expected: Post created successfully

### Expected Result
✅ All validation errors caught and displayed to user

---

## Test Scenario 5: Delete Post

### Goal
Verify post deletion works

### Steps

1. **Create a Draft/Scheduled Post**
   - Follow Test Scenario 2

2. **Delete from Dashboard**
   - Find post in "Your Posts"
   - Click "Delete" button
   - Confirm deletion

3. **Verify Deleted**
   - Post no longer appears in dashboard
   - Refresh page to confirm
   - Check MongoDB: `db.posts.find().count()` should decrease

4. **Try Delete Posted Post**
   - Create and wait for post to be published
   - Try to delete published post
   - Expected: Delete button not available for posted posts

### Expected Result
✅ Can delete scheduled/draft posts, can't delete posted posts

---

## Test Scenario 6: Retry Failed Post

### Goal
Verify retry mechanism for failed posts

### Steps

1. **Force Post Failure**
   ```bash
   # In MongoDB, invalidate user's token
   db.users.updateOne(
     {_id: ObjectId("YOUR_USER_ID")},
     {$set: {linkedin_access_token: "invalid_token_12345"}}
   )
   ```

2. **Create Post**
   - Follow Test Scenario 2
   - Schedule for 1-2 minutes from now

3. **Watch for Failure**
   - Check backend logs:
     ```
     WARN: Post ... failed (attempt 1/3). Retrying in 5s...
     WARN: Post ... failed (attempt 2/3). Retrying in 25s...
     WARN: Post ... failed (attempt 3/3). Retrying in 125s...
     ERROR: ❌ Failed to post after 3 retries
     ```

4. **Verify Failed Status**
   - Dashboard shows post status: "failed"
   - Last error message displayed
   - Retry button available

5. **Manual Retry**
   - Fix user's token in MongoDB:
     ```bash
     # Get valid token from new OAuth login or copy from another user
     db.users.updateOne(
       {_id: ObjectId("YOUR_USER_ID")},
       {$set: {linkedin_access_token: "valid_token_here"}}
     )
     ```
   - Click "Retry" button on failed post
   - Watch logs for success

### Expected Result
✅ Failed post retries automatically, can be manually retried

---

## Test Scenario 7: List and Filter Posts

### Goal
Verify post listing and filtering works

### Steps

1. **Create Multiple Posts**
   - Create 3-4 posts
   - Schedule them for different times (some past, some future)
   - Wait for some to publish

2. **List All Posts**
   - Go to /dashboard/posts
   - Should see all your posts
   - Sorted by creation time (newest first)

3. **Filter by Status**
   - Click "Scheduled" filter
   - Should only show scheduled posts
   - Click "Posted" filter
   - Should only show published posts
   - Click "All" to reset

4. **Pagination**
   - Create many posts (50+)
   - Default shows 20 per page
   - Load more / pagination should work

### Expected Result
✅ Posts listed correctly, filtering works, pagination functional

---

## Test Scenario 8: User Profile

### Goal
Verify user can view their profile

### Steps

1. **Navigate to Navbar**
   - On any dashboard page
   - Navbar shows your name and email

2. **Call /api/me**
   - In browser console:
     ```javascript
     fetch('/api/me', {
       headers: {Authorization: `Bearer ${localStorage.getItem('jwt_token')}`}
     }).then(r => r.json()).then(console.log)
     ```
   - Should return user data with id, name, email, linkedin_id

### Expected Result
✅ User profile accessible and correct

---

## Test Scenario 9: Token Expiration Handling

### Goal
Verify expired tokens are handled gracefully

### Steps

1. **Expire Token Manually**
   ```javascript
   // In browser console
   localStorage.setItem('jwt_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid')
   ```

2. **Try to Access Dashboard**
   - Refresh page or navigate to /dashboard
   - Should be redirected to /login
   - Token cleared from localStorage

3. **Token Refresh on API Call**
   - Make API call with expired token (manual fetch)
   - Expected: 401 Unauthorized response
   - Frontend should redirect to login

### Expected Result
✅ Expired tokens detected, user redirected to login

---

## Test Scenario 10: CORS and API Access

### Goal
Verify CORS is configured correctly

### Steps

1. **Verify API Accessible from Frontend**
   ```javascript
   // In browser console on http://localhost:3000
   fetch('http://localhost:8000/health')
     .then(r => r.json())
     .then(console.log)
   // Should return health check response
   ```

2. **Verify Auth Headers**
   - Network tab should show Authorization headers
   - API calls should include JWT token

3. **Test Invalid Token**
   - Use invalid token in Authorization header
   - API should return 401
   - Frontend should handle gracefully

### Expected Result
✅ CORS working, auth headers sent, invalid tokens rejected

---

## Performance Testing

### Test Load Time

```bash
# Test API response time
# In Terminal:
time curl http://localhost:8000/health

# Expected: < 100ms response time
```

### Test Frontend Load

```javascript
// In browser console:
performance.measure('pageLoad', 'navigationStart', 'loadEventEnd')
performance.getEntriesByName('pageLoad')[0].duration

// Expected: < 3 seconds
```

---

## Error Scenarios

### Test 1: Backend Down
- Stop backend server
- Try to login/create post on frontend
- Expected: Error message displayed, no crash

### Test 2: Database Down
- Disconnect MongoDB
- Try operations on backend
- Expected: Database error shown, graceful handling

### Test 3: Invalid LinkedIn Credentials
- Use wrong OAuth credentials
- Try to login
- Expected: Error message, can retry

### Test 4: LinkedIn API Rate Limited
- Make many requests quickly
- Expected: Rate limit error handled, retry after displayed

---

## Cleanup After Testing

1. **Clear Test Data**
   ```bash
   # Delete test posts
   db.posts.deleteMany({content: {$regex: "Testing"}})
   
   # Delete test users (optional)
   db.users.deleteMany({email: {$regex: "test"}})
   ```

2. **Clear Browser Data**
   - Clear localStorage
   - Clear cookies
   - Clear cache

3. **Reset Tokens**
   - Regenerate LinkedIn OAuth credentials if compromised
   - Rotate JWT secret if exposed

---

## Troubleshooting

### "Cannot GET /dashboard"
- Frontend files not built
- Run `npm run build`
- Check Next.js dev server running

### "API connection refused"
- Backend not running
- Check port 8000
- Verify MongoDB connection

### "Unauthorized" on API calls
- Token expired
- Token invalid
- Frontend not sending token in header

### "LinkedIn login fails"
- OAuth credentials wrong
- redirect_uri misconfigured
- LinkedIn app not approved

---

## Sign-Off

After completing all test scenarios:

- [ ] All tests passed
- [ ] No console errors
- [ ] All error messages clear
- [ ] Performance acceptable
- [ ] Ready for production

**Tested by:** ________________
**Date:** ________________
**Notes:** ________________________________________________________
