import datetime
import numpy as np
from sqlalchemy import select, func, Float
from sqlalchemy.ext.asyncio import AsyncSession
from models import Headline, HeadlineScore, RollingBaseline
from config import settings

async def compute_rolling_baselines(session: AsyncSession):
    # This computes the 30-day mean embedding per sector
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    
    print(f"Starting baseline computation for {len(settings.SECTORS)} sectors...")
    
    for sector in settings.SECTORS:
        # Get all headlines for this sector in the last 30 days
        # We join with headline_scores to get a high probability sector match
        # For simplicity in this version, we'll just average all embeddings that have been 
        # attributed to this sector with > 0.5 probability
        
        stmt = select(Headline.embedding).join(HeadlineScore).where(
            HeadlineScore.sector_probs[sector].astext.cast(Float) >= 0.1,
            Headline.ingested_at >= thirty_days_ago
        )
        
        result = await session.execute(stmt)
        embeddings = result.scalars().all()
        
        if not embeddings:
            print(f"Skipping {sector}: No data in last 30 days.")
            continue
            
        # Average the vectors
        mean_vec = np.mean(embeddings, axis=0).tolist()
        
        # Save to DB
        new_baseline = RollingBaseline(
            sector=sector,
            computed_at=datetime.datetime.utcnow(),
            mean_embedding=mean_vec
        )
        session.add(new_baseline)
        print(f"Updated baseline for {sector} using {len(embeddings)} data points.")
        
    await session.commit()
    print("Baseline computation complete.")
