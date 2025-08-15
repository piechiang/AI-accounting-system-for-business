from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.services.transaction_service import TransactionService
from app.services.data_cleaning_service import DataCleaningService
from app.schemas.transactions import (
    TransactionRawCreate, TransactionRawResponse,
    TransactionCleanResponse, TransactionUploadResponse
)

router = APIRouter()

@router.post("/upload", response_model=TransactionUploadResponse)
async def upload_transactions(
    file: UploadFile = File(...),
    source: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload and process transaction file (CSV/Excel)"""
    transaction_service = TransactionService(db)
    cleaning_service = DataCleaningService()
    
    try:
        # Process uploaded file
        result = await transaction_service.process_upload(file, source)
        
        # Clean and normalize data
        cleaned_count = await cleaning_service.clean_transactions(result['raw_transactions'])
        
        return TransactionUploadResponse(
            success=True,
            message=f"Successfully processed {result['total_count']} transactions",
            total_count=result['total_count'],
            new_count=result['new_count'],
            duplicate_count=result['duplicate_count'],
            cleaned_count=cleaned_count
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/raw", response_model=List[TransactionRawResponse])
def get_raw_transactions(
    skip: int = 0,
    limit: int = 100,
    source: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get raw transactions with filters"""
    transaction_service = TransactionService(db)
    return transaction_service.get_raw_transactions(
        skip=skip, 
        limit=limit, 
        source=source,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/clean", response_model=List[TransactionCleanResponse])
def get_clean_transactions(
    skip: int = 0,
    limit: int = 100,
    classified_only: bool = False,
    reviewed_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get cleaned/processed transactions"""
    transaction_service = TransactionService(db)
    return transaction_service.get_clean_transactions(
        skip=skip,
        limit=limit,
        classified_only=classified_only,
        reviewed_only=reviewed_only
    )

@router.get("/stats")
def get_transaction_stats(db: Session = Depends(get_db)):
    """Get transaction statistics"""
    transaction_service = TransactionService(db)
    return transaction_service.get_transaction_stats()

@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction"""
    transaction_service = TransactionService(db)
    success = transaction_service.delete_transaction(transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}