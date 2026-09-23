"""Create all tables (development helper when Alembic is not yet run)."""
import asyncio
import sys
sys.path.insert(0, "/home/workdir/artifacts/seo-autopilot-ai/backend")

from app.database.session import engine, Base
from app.models import *  # noqa: F401, F403


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
