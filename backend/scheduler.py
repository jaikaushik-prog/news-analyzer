from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pipeline.ingestion import ingest_news
from pipeline.baseline_updater import compute_rolling_baselines
from database import AsyncSessionLocal

scheduler = AsyncIOScheduler()

async def scheduled_ingestion():
    async with AsyncSessionLocal() as session:
        await ingest_news(session)

async def scheduled_baselines():
    async with AsyncSessionLocal() as session:
        await compute_rolling_baselines(session)

def start_scheduler():
    # Ingestion every 15 minutes
    scheduler.add_job(scheduled_ingestion, 'interval', minutes=15, id='news_ingestion')
    # Nightly baselines
    scheduler.add_job(scheduled_baselines, 'cron', hour=2, minute=0, id='nightly_baselines')
    
    scheduler.start()
    print("Scheduler started with ingestion and baseline jobs!")

def shutdown_scheduler():
    scheduler.shutdown()
    print("Scheduler stopped!")
