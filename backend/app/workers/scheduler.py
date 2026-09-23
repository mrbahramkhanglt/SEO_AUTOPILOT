"""Due-schedule runner – call periodically (cron / Celery beat / loop)."""
from __future__ import annotations

import asyncio
import traceback

from app.database.session import AsyncSessionLocal
from app.services.monitoring import list_due_schedules, run_scheduled_crawl


async def run_due_once() -> int:
    """Process all due monitor schedules. Returns number of runs started."""
    count = 0
    async with AsyncSessionLocal() as db:
        due = await list_due_schedules(db)
        for sched in due:
            try:
                crawl_id = await run_scheduled_crawl(db, sched)
                if crawl_id:
                    count += 1
                    print(f"Scheduled crawl {crawl_id} for website {sched.website_id}")
            except Exception:
                traceback.print_exc()
    return count


def main():
    n = asyncio.run(run_due_once())
    print(f"Processed {n} due schedule(s)")


if __name__ == "__main__":
    main()
