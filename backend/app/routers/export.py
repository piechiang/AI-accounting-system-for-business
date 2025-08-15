from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import os

from app.core.database import get_db
from app.services.export_service import ExportService
from app.schemas.export import (
    ExportRequest, ExportResponse,
    QuickBooksExportRequest, XeroExportRequest
)

router = APIRouter()

@router.post("/quickbooks", response_model=ExportResponse)
async def export_to_quickbooks(
    request: QuickBooksExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Export transactions to QuickBooks format"""
    export_service = ExportService(db)
    try:
        result = await export_service.export_to_quickbooks(
            start_date=request.start_date,
            end_date=request.end_date,
            export_type=request.export_type,
            include_categories=request.include_categories,
            reviewed_only=request.reviewed_only
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/xero", response_model=ExportResponse)
async def export_to_xero(
    request: XeroExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Export transactions to Xero format"""
    export_service = ExportService(db)
    try:
        result = await export_service.export_to_xero(
            start_date=request.start_date,
            end_date=request.end_date,
            export_type=request.export_type,
            include_tax_mapping=request.include_tax_mapping,
            reviewed_only=request.reviewed_only
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/download/{file_id}")
async def download_export_file(file_id: str, db: Session = Depends(get_db)):
    """Download exported file"""
    export_service = ExportService(db)
    file_info = export_service.get_export_file_info(file_id)
    
    if not file_info or not os.path.exists(file_info['file_path']):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    return FileResponse(
        path=file_info['file_path'],
        filename=file_info['filename'],
        media_type='application/octet-stream'
    )

@router.get("/formats")
def get_supported_formats():
    """Get supported export formats and their specifications"""
    return {
        "quickbooks": {
            "formats": ["journal_entry", "expense", "bill", "invoice"],
            "required_fields": ["Date", "Account", "Amount", "Description"],
            "optional_fields": ["Memo", "Name", "Class", "Location"]
        },
        "xero": {
            "formats": ["journal_entry", "invoice", "bill", "bank_transaction"],
            "required_fields": ["Date", "Account", "Amount", "Description"], 
            "optional_fields": ["Reference", "TaxType", "Contact"]
        },
        "csv_generic": {
            "formats": ["transactions", "trial_balance", "general_ledger"],
            "customizable": True
        }
    }

@router.post("/csv-generic", response_model=ExportResponse)
async def export_to_csv(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Export to generic CSV format"""
    export_service = ExportService(db)
    try:
        result = await export_service.export_to_csv(
            start_date=request.start_date,
            end_date=request.end_date,
            export_type=request.export_type,
            columns=request.columns,
            filters=request.filters
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history")
def get_export_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get export history"""
    export_service = ExportService(db)
    return export_service.get_export_history(skip=skip, limit=limit)

@router.delete("/cleanup")
def cleanup_old_exports(
    days_old: int = 30,
    db: Session = Depends(get_db)
):
    """Cleanup old export files"""
    export_service = ExportService(db)
    cleaned_count = export_service.cleanup_old_exports(days_old)
    return {"message": f"Cleaned up {cleaned_count} old export files"}