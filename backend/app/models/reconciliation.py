from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(DateTime, nullable=False, index=True)
    debit_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    credit_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    amount_base = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    memo = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)  # Invoice number, etc.
    source = Column(String(50), default="manual")  # manual, import, system
    is_reconciled = Column(String(10), default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    debit_account = relationship("ChartOfAccounts", foreign_keys=[debit_account_id])
    credit_account = relationship("ChartOfAccounts", foreign_keys=[credit_account_id])
    reconciliations = relationship("Reconciliation", back_populates="ledger_entry")

class Reconciliation(Base):
    __tablename__ = "reconciliations"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_clean_id = Column(Integer, ForeignKey("transactions_clean.id"), nullable=False)
    ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True)
    match_type = Column(String(20), nullable=False)  # exact, windowed, fuzzy, manual
    match_score = Column(Float, nullable=False)  # 0.0 to 1.0
    amount_difference = Column(Float, default=0.0)
    date_difference_days = Column(Integer, default=0)
    description_similarity = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    notes = Column(Text, nullable=True)
    reconciled_by = Column(String(100), nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    transaction_clean = relationship("TransactionClean", back_populates="reconciliations")
    ledger_entry = relationship("LedgerEntry", back_populates="reconciliations")