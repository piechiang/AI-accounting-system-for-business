from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

class DashboardSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    total_income: float
    total_expenses: float
    net_income: float
    transaction_count: int
    classified_percentage: float
    reconciled_percentage: float
    top_expense_category: Optional[str]
    largest_transaction: Optional[dict]
    recent_activity_count: int

class ExpenseCategoryResponse(BaseModel):
    category_name: str
    category_code: Optional[str]
    total_amount: float
    transaction_count: int
    percentage_of_total: float
    trend: Optional[str] = None  # up, down, stable

class RevenueAnalysisResponse(BaseModel):
    period: str
    revenue: float
    growth_rate: Optional[float] = None
    transaction_count: int

class AnomalyDetectionResponse(BaseModel):
    transaction_id: int
    anomaly_type: str  # amount, frequency, new_vendor
    description: str
    amount: float
    date: date
    severity: str  # low, medium, high
    reason: str

class CashFlowItem(BaseModel):
    period: str
    cash_in: float
    cash_out: float
    net_cash_flow: float

class VendorAnalysisResponse(BaseModel):
    vendor_name: str
    total_spent: float
    transaction_count: int
    average_amount: float
    last_transaction_date: date
    category: Optional[str] = None

class KPIResponse(BaseModel):
    kpi_name: str
    current_value: float
    previous_value: Optional[float]
    change_percentage: Optional[float]
    trend: Optional[str] = None
    benchmark: Optional[float] = None

class TrendAnalysisResponse(BaseModel):
    category: str
    period: str
    amount: float
    trend_direction: str
    trend_strength: float