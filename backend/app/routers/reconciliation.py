from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.services.reconciliation_service import ReconciliationService
from app.schemas.reconciliation import (
    ReconciliationRequest, ReconciliationResponse,
    ReconciliationReviewRequest, ReconciliationStatsResponse
)

router = APIRouter()

@router.post("/auto-match", response_model=List[ReconciliationResponse])
async def auto_reconcile(
    request: ReconciliationRequest,
    db: Session = Depends(get_db)
):
    """Perform automatic reconciliation"""
    reconciliation_service = ReconciliationService(db)
    try:
        results = await reconciliation_service.auto_reconcile(
            start_date=request.start_date,
            end_date=request.end_date,
            account_ids=request.account_ids,
            min_confidence=request.min_confidence
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/matches", response_model=List[ReconciliationResponse])
def get_reconciliation_matches(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    match_type: Optional[str] = None,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get reconciliation matches with filters"""
    reconciliation_service = ReconciliationService(db)
    return reconciliation_service.get_reconciliation_matches(
        skip=skip,
        limit=limit,
        status=status,
        match_type=match_type,
        min_score=min_score
    )

@router.post("/review")
def review_reconciliation(
    request: ReconciliationReviewRequest,
    db: Session = Depends(get_db)
):
    """Review and approve/reject reconciliation"""
    reconciliation_service = ReconciliationService(db)
    try:
        result = reconciliation_service.review_reconciliation(
            reconciliation_id=request.reconciliation_id,
            status=request.status,
            notes=request.notes,
            reviewed_by=request.reviewed_by
        )
        return {"success": True, "message": f"Reconciliation {request.status}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/unmatched")
def get_unmatched_transactions(
    transaction_type: str = "bank",  # bank or ledger
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get unmatched transactions"""
    reconciliation_service = ReconciliationService(db)
    return reconciliation_service.get_unmatched_transactions(
        transaction_type=transaction_type,
        skip=skip,
        limit=limit
    )

@router.get("/stats", response_model=ReconciliationStatsResponse)
def get_reconciliation_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get reconciliation statistics"""
    reconciliation_service = ReconciliationService(db)
    return reconciliation_service.get_reconciliation_stats(start_date, end_date)

@router.post("/run")
async def run_reconcile(
    request: dict,
    db: Session = Depends(get_db)
):
    """Enhanced reconciliation engine with exact/windowed/fuzzy/partial matching"""
    reconciliation_service = ReconciliationService(db)
    try:
        # Extract parameters with defaults
        start_date = request.get('start_date')
        end_date = request.get('end_date')
        account_ids = request.get('account_ids')
        
        # Algorithm parameters
        amount_tolerance = request.get('amount_tolerance', 0.01)
        date_window_days = request.get('date_window_days', 5)
        fuzzy_threshold = request.get('fuzzy_threshold', 0.85)
        partial_max_txns = request.get('partial_max_txns', 3)
        
        # Weights for unified scoring
        weights = request.get('weights', {
            'exact': 0.5, 'windowed': 0.2, 'fuzzy': 0.2, 'partial': 0.1
        })
        
        result = await reconciliation_service.run_reconcile(
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids,
            amount_tolerance=amount_tolerance,
            date_window_days=date_window_days,
            fuzzy_threshold=fuzzy_threshold,
            partial_max_txns=partial_max_txns,
            weights=weights
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/exceptions")
def get_reconciliation_exceptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get reconciliation exceptions and differences"""
    reconciliation_service = ReconciliationService(db)
    return reconciliation_service.get_reconciliation_exceptions(skip=skip, limit=limit)