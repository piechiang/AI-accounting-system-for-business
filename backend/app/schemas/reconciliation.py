from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class ReconciliationRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    account_ids: Optional[List[int]] = None
    min_confidence: float = Field(default=0.8, ge=0.0, le=1.0)

class ReconciliationResponse(BaseModel):
    id: int
    transaction_clean_id: int
    ledger_entry_id: Optional[int]
    match_type: str
    match_score: float
    amount_difference: float
    date_difference_days: int
    description_similarity: Optional[float]
    status: str
    notes: Optional[str]
    transaction_info: dict
    ledger_info: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True

class ReconciliationReviewRequest(BaseModel):
    reconciliation_id: int
    status: str = Field(regex="^(approved|rejected)$")
    notes: Optional[str] = None
    reviewed_by: str

class ReconciliationStatsResponse(BaseModel):
    total_transactions: int
    total_ledger_entries: int
    matched_count: int
    unmatched_transactions: int
    unmatched_ledger_entries: int
    match_rate: float
    auto_match_rate: float
    manual_review_needed: int
    match_type_breakdown: dict
    accuracy_by_match_type: dict