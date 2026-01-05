from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func

from app.db.base import Base


class PTQADecision(Base):
    """
    Stores the PTQA decision and key metrics for a given healing_id.
    """

    __tablename__ = "ptqa_decisions"

    id = Column(Integer, primary_key=True, index=True)

    # Business key
    healing_id = Column(String, unique=True, index=True, nullable=False)

    # Context
    script_id = Column(String, index=True, nullable=True)
    environment = Column(String, index=True, nullable=True)

    # Prediction
    will_work_probability = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    model_name = Column(String, nullable=True)

    # Metrics
    healing_accuracy = Column(Float, nullable=True)
    recovery_latency = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)

    # Text/JSON fields (we store JSON as text for simplicity)
    validation_steps = Column(Text, nullable=True)  # JSON stringified list
    reasons = Column(Text, nullable=True)          # JSON stringified list
    raw_payload = Column(Text, nullable=True)      # original event JSON

    created_at = Column(DateTime(timezone=True), server_default=func.now())
