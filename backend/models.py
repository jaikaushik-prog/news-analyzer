import uuid
import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from database import Base

class Headline(Base):
    __tablename__ = 'headlines'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    embedding = Column(Vector(384))
    
    # Intentionally ignoring index creation here because we do it in init.sql
    # with specific pgvector instructions.

class HeadlineScore(Base):
    __tablename__ = 'headline_scores'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    headline_id = Column(UUID(as_uuid=True), ForeignKey('headlines.id', ondelete='CASCADE'))
    surprise = Column(Float)
    sentiment = Column(Float)
    sector_probs = Column(JSONB)
    event_type = Column(Text)
    scored_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

class RollingBaseline(Base):
    __tablename__ = 'rolling_baselines'
    sector = Column(Text, primary_key=True)
    computed_at = Column(DateTime(timezone=True), primary_key=True)
    mean_embedding = Column(Vector(384))

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sector = Column(Text, nullable=False)
    triggered_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    surprise_val = Column(Float, nullable=False)
    layers = Column(JSONB)
    rationale = Column(Text)
    headline_ids = Column(ARRAY(UUID(as_uuid=True)))
    conviction = Column(Text)

class FeedMetadata(Base):
    __tablename__ = 'feed_metadata'
    feed_url = Column(Text, primary_key=True)
    etag = Column(Text)
    last_modified = Column(Text)
    last_fetched_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
