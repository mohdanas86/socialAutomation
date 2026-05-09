"""
seed_posts.py
=============
Creates scheduled LinkedIn posts directly in MongoDB.

HOW TO USE
----------
1. Edit CONFIG below — change START_TIME, GAP_MINUTES, or add/remove posts in POSTS
2. Run:  .\\venv\\Scripts\\python.exe seed_posts.py
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.mongodb import connect_to_mongo, disconnect_from_mongo, get_database
from app.models.schemas import PostStatus, PlatformType


# ══════════════════════════════════════════════════════════════
#  CONFIG  — edit this section
# ══════════════════════════════════════════════════════════════

CONFIG = {
    # First post fires at this IST time  (format: YYYY-MM-DD HH:MM)
    "start_time_ist": "2026-05-09 01:20",

    # Minutes between each consecutive post  (can be decimal: 1.5 = 1m 30s)
    "gap_minutes": 1.5,

    # Platform for all posts
    "platform": PlatformType.LINKEDIN,
}

# ──────────────────────────────────────────────────────────────
#  POSTS  — add / remove / edit entries freely
#
#  Each entry is a dict with:
#    title   : short label (shown in console, not posted to LinkedIn)
#    content : the actual post text (max 3000 chars)
# ──────────────────────────────────────────────────────────────

POSTS = [
    {
        "title": "AI as developer co-pilot",
        "content": """\
The future of AI is not replacing developers — it's amplifying them.

I've been experimenting with AI-assisted code reviews for the past month. The result? 40% fewer review cycles and richer feedback than manual passes alone.

Key insight: AI works best as a thinking partner, not a replacement. It surfaces edge cases I'd miss after hour 6 of a sprint.

What tools are you using to keep your code quality high?

#AI #SoftwareEngineering #DeveloperProductivity #Tech""",
    },
    {
        "title": "API documentation as a product",
        "content": """\
Hot take: Your API documentation is a product. Treat it like one.

Too many teams ship great APIs with docs that look like they were written in 2005. Here's what I've learned matters most:

1. Live, runnable examples beat static code snippets every time
2. Error messages should explain *why*, not just *what*
3. Versioning strategy should be in the README, not buried in a wiki

Developers who love your docs will become your strongest advocates.

#APIDevelopment #TechWriting #DeveloperExperience #Backend""",
    },
    {
        "title": "Safe Friday production deploy",
        "content": """\
I deployed to production on a Friday. And nothing broke.

Here's the system that made it possible:
- Feature flags for zero-downtime rollouts
- Canary deployments at 5% -> 25% -> 100%
- Automated rollback triggers on error rate spikes
- Slack alerts piped directly to the on-call channel

Continuous deployment isn't scary when you build the right safety net first.

What's your deployment philosophy?

#DevOps #CI_CD #SoftwareEngineering #CloudInfrastructure""",
    },
    {
        "title": "TypeScript becoming mandatory",
        "content": """\
Unpopular opinion: TypeScript will become mandatory for enterprise JavaScript within 3 years.

The evidence is already there:
- Next.js, Remix, and Astro all default to TypeScript
- Node 22 ships with experimental TS support built in
- Major companies (Stripe, Vercel, Linear) run 100% TS codebases

Type safety isn't just about catching bugs — it's about scaling teams. When 50 engineers touch the same codebase, types are the contract.

Are you still writing plain JS in 2025?

#TypeScript #JavaScript #WebDevelopment #Frontend""",
    },
    {
        "title": "Event-driven microservices",
        "content": """\
The best architecture decision I made last year: event-driven microservices with a message queue.

Before: 12 tightly coupled REST services. One goes down, everything breaks.

After: Each service publishes events. Consumers process at their own pace. Failures isolate cleanly.

The trade-offs are real (eventual consistency is hard), but for high-throughput systems the reliability gains are worth it.

Would love to hear from teams who've gone back to a modular monolith. What drove the decision?

#Microservices #SystemDesign #SoftwareArchitecture #Backend #Tech""",
    },

    # ── Add more posts below this line ───────────────────────
    # {
    #     "title": "My post title",
    #     "content": "Post content here...",
    # },
]


# ══════════════════════════════════════════════════════════════
#  SEED LOGIC  — no need to edit below
# ══════════════════════════════════════════════════════════════

IST = timezone(timedelta(hours=5, minutes=30))


def parse_ist(dt_str: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' as IST and return UTC datetime."""
    local = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return local.astimezone(timezone.utc).replace(tzinfo=None)  # naive UTC


async def seed():
    await connect_to_mongo()
    db = get_database()

    # Get the first user
    user = await db["users"].find_one({})
    if not user:
        print("[ERROR] No users found. Log in at least once before running this script.")
        await disconnect_from_mongo()
        return

    user_id   = str(user["_id"])
    user_name = user.get("name", "Unknown")
    print(f"[OK] User: {user_name} ({user_id})")
    print(f"     Posts to create : {len(POSTS)}")
    print(f"     Start time (IST): {CONFIG['start_time_ist']}")
    print(f"     Gap             : {CONFIG['gap_minutes']} min\n")

    gap_seconds = CONFIG["gap_minutes"] * 60
    base_time   = parse_ist(CONFIG["start_time_ist"])
    posts_col   = db["posts"]

    for i, post_def in enumerate(POSTS):
        scheduled_utc = base_time + timedelta(seconds=gap_seconds * i)
        scheduled_ist = scheduled_utc.replace(tzinfo=timezone.utc).astimezone(IST)

        doc = {
            "user_id":          user_id,
            "content":          post_def["content"].strip(),
            "scheduled_time":   scheduled_utc,
            "status":           PostStatus.SCHEDULED.value,
            "platform":         CONFIG["platform"].value,
            "retry_count":      0,
            "last_error":       None,
            "linkedin_post_id": None,
            "created_at":       datetime.utcnow(),
            "updated_at":       datetime.utcnow(),
            "posted_at":        None,
        }

        result = await posts_col.insert_one(doc)
        print(
            f"  [{i+1}/{len(POSTS)}] {post_def['title'][:45]:<45} "
            f"-> {scheduled_ist.strftime('%d %b %H:%M')} IST"
        )

    print(f"\n[DONE] {len(POSTS)} posts scheduled for {user_name}.")
    await disconnect_from_mongo()


if __name__ == "__main__":
    asyncio.run(seed())
