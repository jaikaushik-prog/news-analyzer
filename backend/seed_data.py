import asyncio
import uuid
import datetime
from database import AsyncSessionLocal
from models import Signal

async def seed_db():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        print("Seeding mock signals...")
        
        mock_signals = [
            Signal(
                id=uuid.uuid4(),
                sector="Tech",
                triggered_at=datetime.datetime.utcnow(),
                surprise_val=0.88,
                layers={"lexical": 0.72, "semantic": 0.85, "event": 0.91},
                rationale="Unexpected surge in semiconductor demand metrics following the Q3 earnings preview. Semantic distance from 30-day baseline indicates a regime shift in sentiment.",
                conviction="high"
            ),
            Signal(
                id=uuid.uuid4(),
                sector="Finance",
                triggered_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
                surprise_val=0.65,
                layers={"lexical": 0.45, "semantic": 0.68, "event": 0.72},
                rationale="Regional banking sector showing elevated lexical surprise scores due to unusual wording in regulatory filings regarding liquidity ratios.",
                conviction="medium"
            )
        ]
        
        session.add_all(mock_signals)
        await session.commit()
        print("Database seeded with 2 mock signals!")

if __name__ == "__main__":
    asyncio.run(seed_db())
