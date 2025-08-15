from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime

from app.core.database import get_db
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    ExpenseCategoryResponse,
    RevenueAnalysisResponse,
    AnomalyDetectionResponse
)

router = APIRouter()

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get dashboard summary with key metrics"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_dashboard_summary(start_date, end_date)

@router.get("/expenses/categories")
def get_expense_categories(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top expense categories"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_expense_categories(start_date, end_date, limit)

@router.get("/revenue/analysis")
def get_revenue_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    group_by: str = "month",  # day, week, month, quarter
    db: Session = Depends(get_db)
):
    """Get revenue analysis over time"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_revenue_analysis(start_date, end_date, group_by)

@router.get("/cash-flow")
def get_cash_flow_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    group_by: str = "month",
    db: Session = Depends(get_db)
):
    """Get cash flow analysis"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_cash_flow_analysis(start_date, end_date, group_by)

@router.get("/anomalies")
def get_anomalies(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    anomaly_types: Optional[str] = None,  # amount,frequency,new_vendor
    db: Session = Depends(get_db)
):
    """Get anomalous transactions"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_anomalies(start_date, end_date, anomaly_types)

@router.get("/vendors/top")
def get_top_vendors(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top vendors by spending"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_top_vendors(start_date, end_date, limit)

@router.get("/trends")
def get_spending_trends(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get spending trends analysis"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_spending_trends(start_date, end_date, category)

@router.get("/kpis")
def get_key_performance_indicators(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    compare_previous_period: bool = True,
    db: Session = Depends(get_db)
):
    """Get key performance indicators"""
    dashboard_service = DashboardService(db)
    return dashboard_service.get_kpis(start_date, end_date, compare_previous_period)