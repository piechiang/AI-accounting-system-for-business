from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    account_type = Column(String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    currency = Column(String(3), default="USD")
    is_active = Column(String(10), default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chart_accounts = relationship("ChartOfAccounts", back_populates="account")

class ChartOfAccounts(Base):
    __tablename__ = "chart_of_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    parent_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    tax_mapping = Column(Text, nullable=True)  # JSON for tax category mappings
    is_active = Column(String(10), default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="chart_accounts")
    parent = relationship("ChartOfAccounts", remote_side=[id])
    classification_rules = relationship("ClassificationRule", back_populates="coa")