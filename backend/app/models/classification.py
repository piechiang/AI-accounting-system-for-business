from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ClassificationRule(Base):
    __tablename__ = "classification_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(255), nullable=False)
    keyword_regex = Column(Text, nullable=False)  # Regex pattern for matching
    suggested_coa_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    confidence = Column(Float, default=1.0)  # Rule-based always high confidence
    priority = Column(Integer, default=100)  # Lower number = higher priority
    is_active = Column(String(10), default="true")
    match_count = Column(Integer, default=0)  # How many times this rule matched
    success_count = Column(Integer, default=0)  # How many times user confirmed
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    coa = relationship("ChartOfAccounts", back_populates="classification_rules")