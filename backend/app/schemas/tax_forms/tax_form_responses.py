from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class ValidationSummary(BaseModel):
    total_issues: int
    errors: int
    warnings: int
    infos: int
    is_valid: bool

class ValidationIssue(BaseModel):
    field: str
    message: str
    rule: str
    severity: str
    current_value: Optional[str] = None
    expected_value: Optional[str] = None

class TaxFormValidationResponse(BaseModel):
    is_valid: bool
    summary: ValidationSummary
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    infos: List[ValidationIssue]

class AdjustmentSummary(BaseModel):
    total_adjustments: int
    total_additions: float
    total_subtractions: float
    net_adjustment: float
    permanent_differences: int
    timing_differences: int

class AdjustmentDetail(BaseModel):
    type: str
    description: str
    amount: float
    explanation: str

class AdjustmentsByType(BaseModel):
    additions: List[AdjustmentDetail]
    subtractions: List[AdjustmentDetail]

class PermanentVsTiming(BaseModel):
    permanent: List[Dict[str, Any]]
    timing: List[Dict[str, Any]]

class M1AdjustmentResponse(BaseModel):
    schedule_m1_data: Dict[str, Any]
    adjustments_summary: AdjustmentSummary
    adjustments_detail: AdjustmentsByType
    permanent_vs_timing: PermanentVsTiming

class TaxFormGenerationResponse(BaseModel):
    form_1120_package: Dict[str, Any]
    validation_summary: ValidationSummary
    validation_errors: List[ValidationIssue]
    validation_warnings: List[ValidationIssue]
    m1_adjustments_summary: Dict[str, Any]

class CorpTaxCalculationResponse(BaseModel):
    taxable_income: float
    tax_liability: float
    effective_rate: float
    marginal_rate: float
    entity_type: str
    tax_year: Optional[int] = None
    note: Optional[str] = None

class BookTaxAnalysisResponse(BaseModel):
    book_income: float
    taxable_income: float
    total_additions: float
    total_subtractions: float
    book_tax_rate_difference: float
    permanent_differences: List[Dict[str, Any]]
    timing_differences: List[Dict[str, Any]]
    risk_indicators: List[str]