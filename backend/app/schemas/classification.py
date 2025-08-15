from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ClassificationRequest(BaseModel):
    transaction_ids: List[int]
    force_reclassify: bool = False

class ClassificationResponse(BaseModel):
    transaction_id: int
    predicted_coa_id: Optional[int]
    predicted_coa_name: Optional[str]
    confidence_score: float
    classification_method: str  # rule, embedding, ml, llm, hybrid
    source: str  # source tag for frontend display
    rule_id: Optional[int] = None
    similarity_score: Optional[float] = None
    reason: Optional[str] = None

class ClassificationRuleCreate(BaseModel):
    rule_name: str
    keyword_regex: str
    suggested_coa_id: int
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = 100
    created_by: str = "user"

class ClassificationRuleResponse(BaseModel):
    id: int
    rule_name: str
    keyword_regex: str
    suggested_coa_id: int
    coa_name: Optional[str]
    confidence: float
    priority: int
    is_active: str
    match_count: int
    success_count: int
    accuracy_rate: Optional[float] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True

class ClassificationReviewRequest(BaseModel):
    transaction_id: int
    correct_coa_id: int
    reviewed_by: str
    notes: Optional[str] = None

class ClassificationApprovalRequest(BaseModel):
    transaction_id: int
    approved_by: str
    create_rule: bool = False
    update_vendor_mapping: bool = False
    notes: Optional[str] = None

class ClassificationAccuracyResponse(BaseModel):
    total_classified: int
    total_reviewed: int
    correct_predictions: int
    accuracy_rate: float
    rule_based_accuracy: float
    ai_based_accuracy: float
    hybrid_accuracy: float