from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TransactionRaw(Base):
    __tablename__ = "transactions_raw"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # bank, credit_card, csv_import
    transaction_date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text, nullable=False)
    counterparty = Column(String(255), nullable=True)
    reference = Column(String(100), nullable=True)  # Check number, transaction ID
    category_raw = Column(String(100), nullable=True)  # Original bank category
    transaction_hash = Column(String(64), unique=True, index=True)  # For deduplication
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    clean_transaction = relationship("TransactionClean", back_populates="raw_transaction", uselist=False)

class TransactionClean(Base):
    __tablename__ = "transactions_clean"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_id = Column(Integer, ForeignKey("transactions_raw.id"), nullable=False)
    transaction_date = Column(DateTime, nullable=False, index=True)
    amount_base = Column(Float, nullable=False)  # Normalized to base currency
    currency_base = Column(String(3), default="USD")
    description_normalized = Column(Text, nullable=False)
    counterparty_normalized = Column(String(255), nullable=True)
    category_predicted = Column(String(100), nullable=True)
    coa_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    confidence_score = Column(Float, nullable=True)
    is_reviewed = Column(String(10), default="false")
    reviewed_by = Column(String(100), nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    raw_transaction = relationship("TransactionRaw", back_populates="clean_transaction")
    coa = relationship("ChartOfAccounts")
    reconciliations = relationship("Reconciliation", back_populates="transaction_clean")