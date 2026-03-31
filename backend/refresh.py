import asyncio
from database import AsyncSessionLocal
from pipeline.ingestion import ingest_news
from pipeline.baseline_updater import compute_rolling_baselines

async def main():
    async with AsyncSessionLocal() as db:
        print("🚀 Starting final ingestion...")
        await ingest_news(db)
        print("📊 Updating sector baselines...")
        await compute_rolling_baselines(db)

if __name__ == "__main__":
    asyncio.run(main())
