from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from decimal import Decimal

from app.core.database import get_db
from app.services.tax_validation_service import TaxFormValidationService
from app.services.book_to_tax_adjustment_service import BookToTaxAdjustmentService
from app.schemas.tax_forms.tax_form_responses import (
    TaxFormValidationResponse,
    M1AdjustmentResponse,
    TaxFormGenerationResponse
)

router = APIRouter()

@router.post("/validate/form-1120", response_model=TaxFormValidationResponse)
async def validate_form_1120(
    form_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Comprehensive validation of Form 1120 including:
    - Field-level validations
    - Business rule checks  
    - Cross-form consistency
    - Calculation verifications
    """
    try:
        validation_service = TaxFormValidationService()
        validation_results = validation_service.validate_form_1120_package(form_data)
        
        validation_report = validation_service.generate_validation_report(validation_results)
        
        return TaxFormValidationResponse(
            is_valid=validation_report["summary"]["is_valid"],
            summary=validation_report["summary"],
            errors=validation_report["errors"],
            warnings=validation_report["warnings"],
            infos=validation_report["infos"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/generate/schedule-m1", response_model=M1AdjustmentResponse)
async def generate_schedule_m1(
    trial_balance: Dict[str, Any],
    book_income: float,
    entity_info: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Generate Schedule M-1 (Book-to-Tax Reconciliation) from trial balance data.
    
    Automatically calculates:
    - Federal tax expense adjustments
    - 50% meals limitation
    - 100% entertainment limitation  
    - Fines and penalties
    - Charitable contribution limitations
    - Tax-exempt income
    - Dividends received deduction
    """
    try:
        adjustment_service = BookToTaxAdjustmentService(db)
        
        # Calculate M-1 adjustments
        adjustments = adjustment_service.calculate_m1_adjustments(
            trial_balance=trial_balance,
            book_income=Decimal(str(book_income)),
            entity_info=entity_info or {}
        )
        
        # Generate M-1 form data
        m1_data = adjustment_service.generate_m1_from_adjustments(
            adjustments, Decimal(str(book_income))
        )
        
        # Generate detailed report
        adjustment_report = adjustment_service.generate_adjustment_report(adjustments)
        
        return M1AdjustmentResponse(
            schedule_m1_data=m1_data,
            adjustments_summary=adjustment_report["summary"],
            adjustments_detail=adjustment_report["adjustments_by_type"],
            permanent_vs_timing=adjustment_report["permanent_vs_timing"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"M-1 generation failed: {str(e)}")

@router.post("/generate/form-1120", response_model=TaxFormGenerationResponse)
async def generate_form_1120_package(
    trial_balance: Dict[str, Any],
    entity_info: Dict[str, Any],
    prior_year_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Generate complete Form 1120 package from trial balance:
    - Form 1120 main form
    - Schedule L (Balance Sheet)
    - Schedule M-1 (Book-to-Tax Reconciliation)  
    - Schedule M-2 (Retained Earnings Analysis)
    
    Includes automatic validations and cross-form tie-outs.
    """
    try:
        # Services
        validation_service = TaxFormValidationService()
        adjustment_service = BookToTaxAdjustmentService(db)
        
        # Extract book income from trial balance
        book_income = Decimal(str(trial_balance.get("net_income", 0)))
        
        # Generate Schedule M-1
        m1_adjustments = adjustment_service.calculate_m1_adjustments(
            trial_balance, book_income, entity_info
        )
        m1_data = adjustment_service.generate_m1_from_adjustments(m1_adjustments, book_income)
        
        # Calculate taxable income after M-1 adjustments
        taxable_income = m1_data["tax_to_book_subtractions"]["line_12"]
        
        # Generate Form 1120 main form (simplified structure)
        form_1120_data = _generate_form_1120_from_tb(trial_balance, taxable_income, entity_info)
        
        # Generate Schedule L (Balance Sheet)
        schedule_l_data = _generate_schedule_l_from_tb(trial_balance, entity_info)
        
        # Generate Schedule M-2 (simplified)
        schedule_m2_data = _generate_schedule_m2(
            prior_year_data or {}, 
            book_income, 
            entity_info.get("distributions", 0)
        )
        
        # Complete form package
        form_package = {
            "form_1120": form_1120_data,
            "schedule_l": schedule_l_data,
            "schedule_m1": m1_data,
            "schedule_m2": schedule_m2_data
        }
        
        # Validate the complete package
        validation_results = validation_service.validate_form_1120_package(form_package)
        validation_report = validation_service.generate_validation_report(validation_results)
        
        return TaxFormGenerationResponse(
            form_1120_package=form_package,
            validation_summary=validation_report["summary"],
            validation_errors=validation_report["errors"],
            validation_warnings=validation_report["warnings"],
            m1_adjustments_summary=adjustment_service.generate_adjustment_report(m1_adjustments)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Form generation failed: {str(e)}")

@router.get("/calculate/corporate-tax")
async def calculate_corporate_tax(
    taxable_income: float = Query(..., description="Taxable income amount"),
    entity_type: str = Query("C-Corp", description="Entity type (C-Corp, S-Corp, etc.)")
):
    """Calculate corporate tax liability based on current tax rates"""
    try:
        if entity_type == "C-Corp":
            # 2023 corporate tax rate is flat 21%
            tax_liability = taxable_income * 0.21
            effective_rate = 0.21 if taxable_income > 0 else 0
            
            return {
                "taxable_income": taxable_income,
                "tax_liability": round(tax_liability, 2),
                "effective_rate": round(effective_rate, 4),
                "marginal_rate": 0.21,
                "entity_type": entity_type,
                "tax_year": 2023
            }
        else:
            # S-Corp, Partnership, etc. are pass-through entities
            return {
                "taxable_income": taxable_income,
                "tax_liability": 0,
                "effective_rate": 0,
                "marginal_rate": 0,
                "entity_type": entity_type,
                "note": "Pass-through entity - tax paid at owner level"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tax calculation failed: {str(e)}")

@router.post("/analyze/book-tax-differences")
async def analyze_book_tax_differences(
    current_year_tb: Dict[str, Any],
    prior_year_tb: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Analyze book-to-tax differences and identify potential issues:
    - Large permanent differences
    - Unusual timing differences
    - Missing common adjustments
    - Compliance risks
    """
    try:
        adjustment_service = BookToTaxAdjustmentService(db)
        
        # Get current year book income
        current_book_income = Decimal(str(current_year_tb.get("net_income", 0)))
        
        # Calculate adjustments
        adjustments = adjustment_service.calculate_m1_adjustments(
            current_year_tb, current_book_income
        )
        
        # Analyze differences
        analysis = {
            "book_income": float(current_book_income),
            "total_additions": sum(float(adj.difference) for adj in adjustments if adj.m1_line in ["line_2", "line_5", "line_6"]),
            "total_subtractions": sum(float(adj.difference) for adj in adjustments if adj.m1_line in ["line_8", "line_9", "line_10"]),
            "permanent_differences": [
                {
                    "type": adj.adjustment_type,
                    "amount": float(adj.difference),
                    "description": adj.description
                }
                for adj in adjustments if adj.permanent
            ],
            "timing_differences": [
                {
                    "type": adj.adjustment_type,
                    "amount": float(adj.difference),
                    "description": adj.description
                }
                for adj in adjustments if not adj.permanent
            ]
        }
        
        # Calculate effective tax rate difference
        taxable_income = current_book_income + Decimal(str(analysis["total_additions"])) - Decimal(str(analysis["total_subtractions"]))
        book_tax_rate_diff = float((taxable_income - current_book_income) / current_book_income) if current_book_income != 0 else 0
        
        analysis["taxable_income"] = float(taxable_income)
        analysis["book_tax_rate_difference"] = book_tax_rate_diff
        
        # Risk indicators
        risks = []
        if analysis["total_additions"] > float(current_book_income) * 0.1:
            risks.append("Large book-to-tax additions (>10% of book income)")
        
        if len([adj for adj in adjustments if adj.adjustment_type == "meals_50_percent"]) == 0 and float(current_year_tb.get("6500", 0)) > 1000:
            risks.append("Potential missing meals limitation adjustment")
            
        analysis["risk_indicators"] = risks
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Helper functions for form generation
def _generate_form_1120_from_tb(trial_balance: Dict[str, Any], taxable_income: float, entity_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Form 1120 structure from trial balance"""
    
    # Extract key amounts from trial balance (simplified mapping)
    gross_receipts = float(trial_balance.get("4000", 0))  # Revenue accounts
    cogs = float(trial_balance.get("5000", 0))  # COGS accounts
    officer_comp = float(trial_balance.get("6100", 0))  # Officer compensation
    salaries = float(trial_balance.get("6110", 0))  # Salaries and wages
    rent = float(trial_balance.get("6200", 0))  # Rent expense
    interest_expense = float(trial_balance.get("6300", 0))  # Interest expense
    
    return {
        "income": {
            "line_1a": gross_receipts,
            "line_1b": 0,  # Returns and allowances
            "line_1c": gross_receipts,  # Net sales
            "line_2": cogs,
            "line_3": gross_receipts - cogs,  # Gross profit
            "line_11": gross_receipts - cogs  # Total income (simplified)
        },
        "deductions": {
            "line_12": officer_comp,
            "line_13": salaries,
            "line_16": rent,
            "line_18": interest_expense,
            "line_27": officer_comp + salaries + rent + interest_expense,  # Total deductions (simplified)
            "line_28": (gross_receipts - cogs) - (officer_comp + salaries + rent + interest_expense),  # Income before special items
            "line_30": taxable_income
        },
        "tax_and_payments": {
            "line_31": taxable_income * 0.21,  # Corporate tax at 21%
            "line_33": 0,  # Total payments
            "line_35": max(0, (taxable_income * 0.21)),  # Amount owed
            "line_36": 0  # Overpayment
        }
    }

def _generate_schedule_l_from_tb(trial_balance: Dict[str, Any], entity_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Schedule L (Balance Sheet) from trial balance"""
    
    # Extract balance sheet accounts (simplified)
    cash = float(trial_balance.get("1000", 0))
    receivables = float(trial_balance.get("1100", 0))
    inventory = float(trial_balance.get("1200", 0))
    fixed_assets = float(trial_balance.get("1500", 0))
    
    accounts_payable = float(trial_balance.get("2000", 0))
    notes_payable = float(trial_balance.get("2100", 0))
    
    # Calculate totals
    total_assets = cash + receivables + inventory + fixed_assets
    total_liabilities = accounts_payable + notes_payable
    equity = total_assets - total_liabilities
    
    return {
        "assets": {
            "line_1": {"col_b": 0, "col_d": cash},  # Cash
            "line_2a": {"col_b": 0, "col_d": receivables},  # Trade notes and accounts receivable
            "line_3": {"col_b": 0, "col_d": inventory},  # Inventories
            "line_10": {"col_b": 0, "col_d": fixed_assets},  # Buildings and other depreciable assets
            "line_15": {"col_b": 0, "col_d": total_assets}  # Total assets
        },
        "liabilities_and_equity": {
            "line_16": {"col_b": 0, "col_d": accounts_payable},  # Accounts payable
            "line_18": {"col_b": 0, "col_d": notes_payable},  # Other current liabilities
            "line_26": {"col_b": 0, "col_d": 0},  # Capital stock
            "line_27": {"col_b": 0, "col_d": equity},  # Retained earnings
            "line_28": {"col_b": 0, "col_d": total_assets}  # Total liabilities and stockholders' equity
        }
    }

def _generate_schedule_m2(prior_year_data: Dict[str, Any], net_income: Decimal, distributions: float) -> Dict[str, Any]:
    """Generate Schedule M-2 (Retained Earnings Analysis)"""
    
    beginning_re = float(prior_year_data.get("retained_earnings", 0))
    ending_re = beginning_re + float(net_income) - distributions
    
    return {
        "beginning_balance": {
            "line_1": beginning_re
        },
        "additions_to_retained_earnings": {
            "line_2": float(net_income),  # Net income per books
            "line_4": float(net_income)  # Total increases
        },
        "subtractions_from_retained_earnings": {
            "line_5": distributions,  # Distributions to shareholders
            "line_9": distributions  # Total decreases
        },
        "ending_balance": {
            "line_10": ending_re
        }
    }