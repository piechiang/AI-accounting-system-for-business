from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class ExportRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    export_type: str = Field(..., regex="^(transactions|trial_balance|general_ledger)$")
    columns: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None

class QuickBooksExportRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    export_type: str = Field(..., regex="^(journal_entry|expense|bill|invoice)$")
    include_categories: bool = True
    reviewed_only: bool = False

class XeroExportRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    export_type: str = Field(..., regex="^(journal_entry|invoice|bill|bank_transaction)$")
    include_tax_mapping: bool = True
    reviewed_only: bool = False

class ExportResponse(BaseModel):
    success: bool
    message: str
    file_id: str
    filename: str
    record_count: int
    file_size: Optional[int] = None
    download_url: str
    expires_at: datetime

class ExportHistoryItem(BaseModel):
    id: int
    export_type: str
    format_type: str
    filename: str
    record_count: int
    file_size: Optional[int]
    created_at: datetime
    downloaded_at: Optional[datetime]
    expires_at: datetime
    status: str