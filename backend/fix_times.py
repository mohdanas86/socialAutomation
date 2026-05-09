"""
Diagnose and fix the scheduled_time offset issue in existing posts.

The seed script stored IST times as if they were UTC (naive datetime).
So scheduled_time in DB is 5:30h AHEAD of what it should be.
posted_at is the actual UTC time stamped by the scheduler = correct.

Fix: subtract 5:30h from scheduled_time for all naive-stored posts where
     scheduled_time is > posted_at (impossible in a real system).
"""
import asyncio
import os
import sys
from datetime import timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("ENVIRONMENT", "development")

IST_OFFSET = timedelta(hours=5, minutes=30)


async def main():
    from app.db.mongodb import connect_to_mongo, disconnect_from_mongo, get_database
    await connect_to_mongo()
    db = get_database()
    posts_col = db["posts"]

    posts = await posts_col.find({}).to_list(length=None)
    print(f"Found {len(posts)} posts\n")

    fixed = 0
    for p in posts:
        pid = p["_id"]
        st  = p.get("scheduled_time")   # stored naive — may be IST-as-UTC
        pa  = p.get("posted_at")         # stored naive — correct UTC
        ca  = p.get("created_at")        # stored naive — correct UTC

        print(f"Post {pid}:")
        print(f"  status       : {p.get('status')}")
        print(f"  scheduled_time (DB) : {st}  tzinfo={getattr(st,'tzinfo',None)}")
        print(f"  posted_at (DB)      : {pa}  tzinfo={getattr(pa,'tzinfo',None)}")

        # Detect if scheduled_time is 5:30h ahead of posted_at (was stored as IST, not UTC)
        if st and pa and st.tzinfo is None and pa.tzinfo is None:
            diff = st - pa
            print(f"  diff scheduled-posted: {diff}")
            # If diff is close to +5:30 it means scheduled_time was stored as IST
            if timedelta(hours=5) <= diff <= timedelta(hours=6):
                correct_scheduled = st - IST_OFFSET
                print(f"  >> FIXING: {st} -> {correct_scheduled} (subtracting IST offset)")
                await posts_col.update_one(
                    {"_id": pid},
                    {"$set": {"scheduled_time": correct_scheduled}}
                )
                fixed += 1
            else:
                print(f"  >> OK (diff not in IST-offset range, no fix needed)")
        else:
            print(f"  >> SKIP (no posted_at or already tz-aware)")
        print()

    print(f"Fixed {fixed} posts.")
    await disconnect_from_mongo()


if __name__ == "__main__":
    asyncio.run(main())
