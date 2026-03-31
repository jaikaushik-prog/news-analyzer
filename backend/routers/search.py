from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Headline
from pipeline.embedder import embedder

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/")
async def search_headlines(q: str = Query(..., min_length=3), db: AsyncSession = Depends(get_db)):
    # 1. Embed query
    query_vector = embedder.encode_one(q)
    
    # 2. pgvector nearest neighbors
    # stmt = select(Headline).order_by(Headline.embedding.cosine_distance(query_vector)).limit(20)
    # result = await db.execute(stmt)
    # headlines = result.scalars().all()
    
    # We will mock the return for now
    return {
        "query": q,
        "results": [] # list of matches
    }
