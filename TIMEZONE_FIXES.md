# Production-Grade Timezone Fixes

## Problems Fixed

### 1. Frontend Date Picker (DatePickerTime.tsx)
**Issue**: String manipulation could corrupt dates during selections.
**Fix**: Rewrote to use proper Date objects throughout, only convert to strings at boundaries.

### 2. Timezone Conversion Logic (create/page.tsx)
**Issue**: Offset calculation was incorrect, causing dates to shift by up to 10 days.
**Fix**: Corrected the formula:
```
UTC = Local + getTimezoneOffset()
```
Added comprehensive console logging for debugging.

### 3. Scheduler Loading (scheduler.py)  
**Issue**: Only past scheduled posts were loaded on app restart, future posts were lost.
**Fix**: Created `get_all_scheduled_posts()` to load ALL posts (past + future) on startup.

## How It Works Now

### Frontend Flow (GMT+5:30 example)
1. User selects: **May 5, 2026 at 5:08 AM**
2. Date picker stores: `"2026-05-05T05:08"` (local time format)
3. On submit, `localToIso()` converts:
   - Parse: year=2026, month=5, day=5, hour=5, min=8
   - Create local Date: `new Date(2026, 4, 5, 5, 8, 0, 0)` → May 5, 5:08 AM
   - Get offset: `-330` minutes (GMT+5:30 = 5.5 hours ahead)
   - Calculate UTC: `5:08 AM + (-5.5 hours)` = May 4, 11:38 PM UTC
   - Send to backend: `"2026-05-04T23:38:00.000Z"`

4. Console logs show every step (check browser DevTools → Console)

### Backend Processing
1. Receives: `"2026-05-04T23:38:00.000Z"`
2. Pydantic parses as UTC datetime
3. Stores in MongoDB: `2026-05-04T23:38:00+00:00` (UTC)
4. Schedules job in APScheduler for May 4, 11:38 PM UTC

### Frontend Display
1. Fetches from API: `"2026-05-04T23:38:00.000Z"` (UTC)
2. `formatTime()` converts: UTC + 5:30 offset = May 5, 5:08 AM GMT+5:30 ✓
3. Shows: **May 5, 5:08 AM GMT+5:30**

## Testing Steps

### Step 1: Create a Test Post
1. Go to Dashboard → Create Post
2. Write some content
3. **Pick a specific date/time**: e.g., **May 15, 2:30 PM**
4. Open **Browser DevTools** → **Console tab**
5. Look for logs like:
   ```
   [DatePicker] Date selected: 2026-05-15T14:30
   [localToIso] Input: 2026-05-15T14:30
   [localToIso] Parsed: year=2026, month=5, day=15, hour=14, min=30
   [localToIso] Timezone offset: -330 min (-5.5 hours)
   [localToIso] UTC ISO: 2026-05-15T09:00:00.000Z
   [handleSubmit] Scheduled time (local): 2026-05-15T14:30
   [handleSubmit] Scheduled time (UTC): 2026-05-15T09:00:00.000Z
   ```
6. Submit the post

### Step 2: Verify Frontend Display
1. Go to Dashboard → Your Posts
2. Find your new post
3. **Verify it shows**: `Scheduled: May 15, 2:30 PM GMT+5:30`
   - Should match the time you picked exactly
   - If it shows a different day/time, there's still an issue

### Step 3: Verify Backend Storage
1. Open a Terminal/Command Prompt
2. Connect to MongoDB (or use MongoDB Compass)
3. Query: `db.posts.findOne({"content": {$regex: "your post content"}})`
4. Look for `scheduled_time` field
5. **Should show**: `ISODate("2026-05-15T09:00:00Z")`
   - This is 2:30 PM - 5:30 hours = 9:00 AM UTC ✓

### Step 4: Check Scheduler Jobs
1. Go to: `http://localhost:8000/debug/scheduler-jobs` (development)
   or `https://linkautomation.netlify.app/api/debug/scheduler-jobs` (production)
2. You should see your post scheduled with:
   - `next_run_time: 2026-05-15 09:00:00+00:00`
   - Job is scheduled for 9:00 AM UTC

### Step 5: Verify Accuracy Over Time
Create posts for different times across multiple days:
- **Today, 6:00 PM** → Should post today at 6 PM local
- **Tomorrow, 10:00 AM** → Should post tomorrow at 10 AM local
- **Next week, 3:00 PM** → Should post next week at 3 PM local

Check that all show correct times in:
- Frontend (Your Posts page)
- Browser logs during creation
- Database (raw `scheduled_time` value)
- Scheduler jobs list

## Debug Endpoints

### Check Scheduler Jobs
```
GET /debug/scheduler-jobs
```
Shows all jobs in the queue with their scheduled times.

### Test Timezone Conversion (Backend)
```
POST /debug/test-timezone-conversion?scheduled_time=2026-05-15T09:00:00Z
```
Test how the backend interprets a UTC datetime.

### View User's Posts (Raw)
```
GET /api/posts
```
Shows all posts with exact times as stored in database.

## Production Checklist

- [x] Frontend date picker uses proper Date objects
- [x] Timezone conversion formula is correct
- [x] Console logging shows conversion steps
- [x] Backend stores UTC correctly
- [x] Frontend displays converted local time correctly  
- [x] Scheduler loads all future posts on startup
- [x] Timezone offset calculation is correct (-330 for GMT+5:30)
- [x] Debug endpoints available for verification

## Common Issues & Fixes

### Issue: Times off by exactly 5:30 hours
**Cause**: Offset applied backwards
**Fix**: Already applied - verify latest code is deployed

### Issue: Times off by 10+ days
**Cause**: Date picker corrupting the date
**Fix**: DatePickerTime.tsx rewritten to use Date objects properly

### Issue: Old posts not scheduled on restart
**Cause**: Only loading past posts
**Fix**: Now loads ALL scheduled posts (past + future)

### Issue: Times still showing wrong
**Steps**:
1. Check browser console for conversion logs
2. Check database for actual stored time
3. Compare: (picked time - 5:30 hours) should equal stored time
4. Run `/debug/test-timezone-conversion` endpoint

## Files Modified

1. `front/components/date-picker-time.tsx` - Fixed date picker
2. `front/app/dashboard/create/page.tsx` - Fixed timezone conversion + logging
3. `backend/app/scheduler/scheduler.py` - Fixed post loading on startup
4. `backend/app/api/routes.py` - Added debug endpoints
