import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, Float
from database import get_db
from models import Headline, HeadlineScore
from config import settings

router = APIRouter(prefix="/sector", tags=["sectors"])

@router.get("/{sector_name}")
async def get_sector_data(sector_name: str, db: AsyncSession = Depends(get_db)):
    if sector_name not in settings.SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found")
        
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    
    # 1. Fetch Trend Data (Sentiment and Surprise over last 7 days)
    # We cast ingested_at to Date for grouping
    trend_stmt = select(
        func.date(Headline.ingested_at).label('day'),
        func.avg(HeadlineScore.sentiment).label('avg_sentiment'),
        func.avg(HeadlineScore.surprise).label('avg_surprise')
    ).join(HeadlineScore).where(
        HeadlineScore.sector_probs[sector_name].astext.cast(Float) >= 0.1,
        Headline.ingested_at >= seven_days_ago
    ).group_by(func.date(Headline.ingested_at)).order_by('day')
    
    trend_res = await db.execute(trend_stmt)
    trend_data = trend_res.all()
    
    sentiment_trend = [
        {"date": row.day.isoformat(), "sentiment": float(row.avg_sentiment), "surprise": float(row.avg_surprise)} 
        for row in trend_data
    ]
    
    # 2. Fetch Recent Headlines
    headline_stmt = select(Headline.raw_text, Headline.published_at).join(HeadlineScore).where(
        HeadlineScore.sector_probs[sector_name].astext.cast(Float) >= 0.1
    ).order_by(desc(Headline.published_at)).limit(10)
    
    headline_res = await db.execute(headline_stmt)
    recent_headlines = [{"text": row.raw_text, "date": row.published_at.isoformat()} for row in headline_res]
    
    return {
        "sector": sector_name,
        "sentiment_trend": sentiment_trend,
        "recent_headlines": recent_headlines
    }
