from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.services.classification_service import ClassificationService
from app.schemas.classification import (
    ClassificationRequest, ClassificationResponse,
    ClassificationRuleCreate, ClassificationRuleResponse,
    ClassificationReviewRequest
)

router = APIRouter()

@router.post("/classify", response_model=List[ClassificationResponse])
async def classify_transactions(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """Classify transactions using rules + AI"""
    classification_service = ClassificationService(db)
    try:
        results = await classification_service.classify_transactions(
            transaction_ids=request.transaction_ids,
            force_reclassify=request.force_reclassify
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/review")
def review_classification(
    request: ClassificationReviewRequest,
    db: Session = Depends(get_db)
):
    """Review and confirm/correct classification"""
    classification_service = ClassificationService(db)
    try:
        result = classification_service.review_classification(
            transaction_id=request.transaction_id,
            correct_coa_id=request.correct_coa_id,
            reviewed_by=request.reviewed_by
        )
        return {"success": True, "message": "Classification reviewed", "learned": result['rule_learned']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rules", response_model=List[ClassificationRuleResponse])
def get_classification_rules(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get classification rules"""
    classification_service = ClassificationService(db)
    return classification_service.get_classification_rules(skip=skip, limit=limit, active_only=active_only)

@router.post("/rules", response_model=ClassificationRuleResponse)
def create_classification_rule(
    rule: ClassificationRuleCreate,
    db: Session = Depends(get_db)
):
    """Create new classification rule"""
    classification_service = ClassificationService(db)
    try:
        created_rule = classification_service.create_classification_rule(rule)
        return created_rule
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/rules/{rule_id}")
def update_classification_rule(
    rule_id: int,
    rule: ClassificationRuleCreate,
    db: Session = Depends(get_db)
):
    """Update classification rule"""
    classification_service = ClassificationService(db)
    updated_rule = classification_service.update_classification_rule(rule_id, rule)
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return updated_rule

@router.delete("/rules/{rule_id}")
def delete_classification_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete classification rule"""
    classification_service = ClassificationService(db)
    success = classification_service.delete_classification_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}

@router.get("/accuracy")
def get_classification_accuracy(db: Session = Depends(get_db)):
    """Get classification accuracy metrics"""
    classification_service = ClassificationService(db)
    return classification_service.get_accuracy_metrics()