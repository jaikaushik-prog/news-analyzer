from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import Signal, Headline
from pipeline.signal_generator import generator

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("/")
async def get_signals(
    sector: str = None,
    conviction: str = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Signal).order_by(desc(Signal.triggered_at))
    if sector:
        stmt = stmt.where(Signal.sector == sector)
    if conviction:
        stmt = stmt.where(Signal.conviction == conviction)
        
    result = await db.execute(stmt)
    signals = result.scalars().all()
    
    # Enrich signals with the first headline text
    enriched_signals = []
    for s in signals:
        h_text = "Complex Multi-Source Event"
        if s.headline_ids and len(s.headline_ids) > 0:
            h_stmt = select(Headline.raw_text).where(Headline.id == s.headline_ids[0])
            h_res = await db.execute(h_stmt)
            h_text = h_res.scalar() or h_text
            
        enriched_signals.append({
            "id": str(s.id), 
            "sector": s.sector, 
            "triggered_at": s.triggered_at.isoformat() if s.triggered_at else None, 
            "surprise_val": s.surprise_val, 
            "layers": s.layers, 
            "rationale": s.rationale, 
            "conviction": s.conviction,
            "headline_text": h_text
        })
    
    return enriched_signals

@router.get("/{signal_id}/rationale")
async def get_signal_rationale(signal_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Signal).where(Signal.id == signal_id)
    result = await db.execute(stmt)
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    if signal.rationale:
        return {"rationale": signal.rationale}
        
    # Lazy generate
    # We should get the headlines
    if signal.headline_ids:
        h_stmt = select(Headline).where(Headline.id.in_(signal.headline_ids))
        h_result = await db.execute(h_stmt)
        headlines = h_result.scalars().all()
        texts = [h.raw_text for h in headlines]
    else:
        texts = []
        
    rationale = await generator.generate_rationale(signal.sector, signal.surprise_val, signal.layers or {}, texts)
    
    # Update
    signal.rationale = rationale
    await db.commit()
    
    return {"rationale": rationale}
