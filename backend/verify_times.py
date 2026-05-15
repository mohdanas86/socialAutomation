import asyncio, os, sys
sys.path.insert(0, '.')
os.environ.setdefault("ENVIRONMENT", "development")
from datetime import timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
FMT = "%b %d %I:%M %p IST"

async def check():
    from app.db.mongodb import connect_to_mongo, get_database
    await connect_to_mongo()
    db = get_database()
    print("After fix - all times in IST:")
    async for p in db["posts"].find({}).sort("created_at", -1):
        st = p.get("scheduled_time")
        pa = p.get("posted_at")
        st_str = st.replace(tzinfo=timezone.utc).astimezone(IST).strftime(FMT) if st else "N/A"
        pa_str = pa.replace(tzinfo=timezone.utc).astimezone(IST).strftime(FMT) if pa else "N/A"
        print(f"  Scheduled : {st_str}")
        print(f"  Published : {pa_str}")
        print()

asyncio.run(check())
