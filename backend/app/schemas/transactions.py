from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

class TransactionRawCreate(BaseModel):
    source: str
    transaction_date: datetime
    amount: float
    currency: str = "USD"
    description: str
    counterparty: Optional[str] = None
    reference: Optional[str] = None
    category_raw: Optional[str] = None

class TransactionRawResponse(BaseModel):
    id: int
    source: str
    transaction_date: datetime
    amount: float
    currency: str
    description: str
    counterparty: Optional[str]
    reference: Optional[str]
    category_raw: Optional[str]
    transaction_hash: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class TransactionCleanResponse(BaseModel):
    id: int
    raw_id: int
    transaction_date: datetime
    amount_base: float
    currency_base: str
    description_normalized: str
    counterparty_normalized: Optional[str]
    category_predicted: Optional[str]
    coa_id: Optional[int]
    coa_name: Optional[str] = None
    confidence_score: Optional[float]
    is_reviewed: str
    reviewed_by: Optional[str]
    processed_at: datetime

    class Config:
        from_attributes = True

class TransactionUploadResponse(BaseModel):
    success: bool
    message: str
    total_count: int
    new_count: int
    duplicate_count: int
    cleaned_count: int

class TransactionStatsResponse(BaseModel):
    total_raw: int
    total_clean: int
    classified_count: int
    reviewed_count: int
    classification_rate: float
    review_rate: float
    date_range: dict