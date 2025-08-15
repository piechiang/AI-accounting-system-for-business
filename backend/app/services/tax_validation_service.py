import json
import os
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum

class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationResult:
    field: str
    severity: ValidationSeverity
    message: str
    rule: str
    current_value: Any = None
    expected_value: Any = None

class TaxFormValidationService:
    """
    Professional-grade tax form validation service that ensures:
    - Field-level validations (type, range, required)
    - Cross-form tie-outs (Schedule L to M-2, M-1 to Form 1120)
    - Calculation validations
    - Business rule validations
    """
    
    def __init__(self):
        self.schemas = {}
        self.load_schemas()
        
    def load_schemas(self):
        """Load all tax form schemas"""
        schema_dir = "app/schemas/tax_forms"
        schema_files = {
            "form_1120": "form_1120_schema.json",
            "schedule_l": "schedule_l_schema.json", 
            "schedule_m1": "schedule_m1_schema.json",
            "schedule_m2": "schedule_m2_schema.json"
        }
        
        for form_name, file_name in schema_files.items():
            file_path = os.path.join(schema_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.schemas[form_name] = json.load(f)
    
    def validate_form_1120_package(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate complete Form 1120 package including:
        - Form 1120 main form
        - Schedule L (Balance Sheet)
        - Schedule M-1 (Book-to-Tax Reconciliation)
        - Schedule M-2 (Retained Earnings Analysis)
        """
        results = []
        
        # Extract form sections
        form_1120 = form_data.get('form_1120', {})
        schedule_l = form_data.get('schedule_l', {})
        schedule_m1 = form_data.get('schedule_m1', {})
        schedule_m2 = form_data.get('schedule_m2', {})
        
        # Validate individual forms
        results.extend(self.validate_form_1120(form_1120))
        results.extend(self.validate_schedule_l(schedule_l))
        results.extend(self.validate_schedule_m1(schedule_m1))
        results.extend(self.validate_schedule_m2(schedule_m2))
        
        # Cross-form validations
        results.extend(self.validate_cross_form_ties(form_1120, schedule_l, schedule_m1, schedule_m2))
        
        return results
    
    def validate_form_1120(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Form 1120 main form"""
        results = []
        schema = self.schemas.get('form_1120', {})
        
        # Validate income section
        income_data = form_data.get('income', {})
        results.extend(self._validate_section(income_data, schema.get('income_section', {}), 'income'))
        
        # Validate deduction section  
        deduction_data = form_data.get('deductions', {})
        results.extend(self._validate_section(deduction_data, schema.get('deduction_section', {}), 'deductions'))
        
        # Validate tax and payments section
        tax_data = form_data.get('tax_and_payments', {})
        results.extend(self._validate_section(tax_data, schema.get('tax_and_payments_section', {}), 'tax_and_payments'))
        
        # Validate business rules
        results.extend(self._validate_form_1120_business_rules(form_data))
        
        return results
    
    def validate_schedule_l(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Schedule L (Balance Sheet)"""
        results = []
        schema = self.schemas.get('schedule_l', {})
        
        # Validate assets section
        assets_data = schedule_data.get('assets', {})
        results.extend(self._validate_section(assets_data, schema.get('assets', {}), 'schedule_l.assets'))
        
        # Validate liabilities and equity section
        liab_equity_data = schedule_data.get('liabilities_and_equity', {})  
        results.extend(self._validate_section(liab_equity_data, schema.get('liabilities_and_equity', {}), 'schedule_l.liabilities_and_equity'))
        
        # Balance sheet balance validation
        results.extend(self._validate_balance_sheet_balance(schedule_data))
        
        return results
    
    def validate_schedule_m1(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Schedule M-1 (Book-to-Tax Reconciliation)"""
        results = []
        schema = self.schemas.get('schedule_m1', {})
        
        # Validate book to tax additions
        additions_data = schedule_data.get('book_to_tax_additions', {})
        results.extend(self._validate_section(additions_data, schema.get('book_to_tax_additions', {}), 'schedule_m1.additions'))
        
        # Validate tax to book subtractions  
        subtractions_data = schedule_data.get('tax_to_book_subtractions', {})
        results.extend(self._validate_section(subtractions_data, schema.get('tax_to_book_subtractions', {}), 'schedule_m1.subtractions'))
        
        # Validate reconciliation math
        results.extend(self._validate_m1_reconciliation(schedule_data))
        
        return results
    
    def validate_schedule_m2(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Schedule M-2 (Retained Earnings Analysis)"""
        results = []
        schema = self.schemas.get('schedule_m2', {})
        
        # Validate all sections
        for section_name in ['beginning_balance', 'additions_to_retained_earnings', 'subtractions_from_retained_earnings', 'ending_balance']:
            section_data = schedule_data.get(section_name, {})
            section_schema = schema.get(section_name, {})
            results.extend(self._validate_section(section_data, section_schema, f'schedule_m2.{section_name}'))
        
        # Validate retained earnings rollforward
        results.extend(self._validate_m2_rollforward(schedule_data))
        
        return results
    
    def validate_cross_form_ties(self, form_1120: Dict, schedule_l: Dict, schedule_m1: Dict, schedule_m2: Dict) -> List[ValidationResult]:
        """Validate cross-form tie-outs and consistency"""
        results = []
        
        # Schedule M-1 Line 12 should equal Form 1120 Line 30 (Taxable Income)
        m1_taxable_income = self._get_decimal(schedule_m1, 'tax_to_book_subtractions.line_12', 0)
        form_taxable_income = self._get_decimal(form_1120, 'deductions.line_30', 0)
        
        if m1_taxable_income != form_taxable_income:
            results.append(ValidationResult(
                field="schedule_m1.line_12",
                severity=ValidationSeverity.ERROR,
                message=f"Schedule M-1 taxable income ({m1_taxable_income:,.2f}) does not equal Form 1120 Line 30 ({form_taxable_income:,.2f})",
                rule="m1_form_1120_tie",
                current_value=m1_taxable_income,
                expected_value=form_taxable_income
            ))
        
        # Schedule M-2 Line 1 should equal Schedule L Line 28 Column B (Beginning Retained Earnings)
        m2_beginning_re = self._get_decimal(schedule_m2, 'beginning_balance.line_1', 0)
        l_beginning_re = self._get_decimal(schedule_l, 'liabilities_and_equity.line_28_col_b', 0)
        
        if m2_beginning_re != l_beginning_re:
            results.append(ValidationResult(
                field="schedule_m2.line_1", 
                severity=ValidationSeverity.ERROR,
                message=f"Schedule M-2 beginning RE ({m2_beginning_re:,.2f}) does not equal Schedule L beginning RE ({l_beginning_re:,.2f})",
                rule="m2_schedule_l_beginning_tie",
                current_value=m2_beginning_re,
                expected_value=l_beginning_re
            ))
        
        # Schedule M-2 Line 10 should equal Schedule L Line 28 Column D (Ending Retained Earnings)
        m2_ending_re = self._get_decimal(schedule_m2, 'ending_balance.line_10', 0)
        l_ending_re = self._get_decimal(schedule_l, 'liabilities_and_equity.line_28_col_d', 0)
        
        if m2_ending_re != l_ending_re:
            results.append(ValidationResult(
                field="schedule_m2.line_10",
                severity=ValidationSeverity.ERROR, 
                message=f"Schedule M-2 ending RE ({m2_ending_re:,.2f}) does not equal Schedule L ending RE ({l_ending_re:,.2f})",
                rule="m2_schedule_l_ending_tie",
                current_value=m2_ending_re,
                expected_value=l_ending_re
            ))
        
        # Schedule M-2 Line 2 should equal Schedule M-1 Line 1 (Net Income per Books)
        m2_net_income = self._get_decimal(schedule_m2, 'additions_to_retained_earnings.line_2', 0)
        m1_net_income = self._get_decimal(schedule_m1, 'book_to_tax_additions.line_1', 0)
        
        if m2_net_income != m1_net_income:
            results.append(ValidationResult(
                field="schedule_m2.line_2",
                severity=ValidationSeverity.ERROR,
                message=f"Schedule M-2 net income ({m2_net_income:,.2f}) does not equal Schedule M-1 net income ({m1_net_income:,.2f})",
                rule="m2_m1_net_income_tie", 
                current_value=m2_net_income,
                expected_value=m1_net_income
            ))
        
        return results
    
    def _validate_section(self, data: Dict[str, Any], schema: Dict[str, Any], section_name: str) -> List[ValidationResult]:
        """Validate a form section against its schema"""
        results = []
        
        for field_name, field_schema in schema.items():
            if isinstance(field_schema, dict) and 'validation' in field_schema:
                field_value = data.get(field_name)
                validation = field_schema['validation']
                
                # Required field check
                if validation.get('required', False) and (field_value is None or field_value == ''):
                    results.append(ValidationResult(
                        field=f"{section_name}.{field_name}",
                        severity=ValidationSeverity.ERROR,
                        message=f"Required field {field_schema.get('description', field_name)} is missing",
                        rule="required_field",
                        current_value=field_value
                    ))
                    continue
                
                if field_value is not None and field_value != '':
                    # Type validation
                    if validation.get('type') == 'currency':
                        try:
                            decimal_value = Decimal(str(field_value))
                            
                            # Min value check
                            if 'min' in validation and decimal_value < Decimal(str(validation['min'])):
                                results.append(ValidationResult(
                                    field=f"{section_name}.{field_name}",
                                    severity=ValidationSeverity.ERROR,
                                    message=f"{field_schema.get('description', field_name)} cannot be less than {validation['min']}",
                                    rule="min_value",
                                    current_value=decimal_value,
                                    expected_value=validation['min']
                                ))
                            
                            # Max value check
                            if 'max' in validation and decimal_value > Decimal(str(validation['max'])):
                                results.append(ValidationResult(
                                    field=f"{section_name}.{field_name}",
                                    severity=ValidationSeverity.ERROR,
                                    message=f"{field_schema.get('description', field_name)} cannot be greater than {validation['max']}",
                                    rule="max_value",
                                    current_value=decimal_value,
                                    expected_value=validation['max']
                                ))
                            
                        except (ValueError, TypeError):
                            results.append(ValidationResult(
                                field=f"{section_name}.{field_name}",
                                severity=ValidationSeverity.ERROR,
                                message=f"{field_schema.get('description', field_name)} must be a valid currency amount",
                                rule="invalid_currency",
                                current_value=field_value
                            ))
                
                # Auto-calculation check
                if validation.get('auto_calculate') and 'calculation' in validation:
                    expected_value = self._evaluate_calculation(validation['calculation'], data)
                    if expected_value is not None and field_value != expected_value:
                        results.append(ValidationResult(
                            field=f"{section_name}.{field_name}",
                            severity=ValidationSeverity.WARNING,
                            message=f"{field_schema.get('description', field_name)} calculation may be incorrect",
                            rule="calculation_check",
                            current_value=field_value,
                            expected_value=expected_value
                        ))
        
        return results
    
    def _validate_balance_sheet_balance(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate that assets equal liabilities + equity"""
        results = []
        
        total_assets = self._get_decimal(schedule_data, 'assets.line_17', 0)
        total_liab_equity = self._get_decimal(schedule_data, 'liabilities_and_equity.line_31', 0)
        
        if total_assets != total_liab_equity:
            results.append(ValidationResult(
                field="schedule_l.balance",
                severity=ValidationSeverity.ERROR,
                message=f"Balance sheet does not balance. Assets ({total_assets:,.2f}) ≠ Liabilities + Equity ({total_liab_equity:,.2f})",
                rule="balance_sheet_balance",
                current_value=total_assets - total_liab_equity
            ))
        
        return results
    
    def _validate_form_1120_business_rules(self, form_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Form 1120 specific business rules"""
        results = []
        
        # Charitable contributions limitation (10% of taxable income before contributions)
        charitable_contributions = self._get_decimal(form_data, 'deductions.line_19', 0)
        taxable_income_before_charity = self._get_decimal(form_data, 'deductions.line_28', 0) + charitable_contributions
        charity_limit = taxable_income_before_charity * Decimal('0.10')
        
        if charitable_contributions > charity_limit:
            results.append(ValidationResult(
                field="deductions.line_19",
                severity=ValidationSeverity.WARNING,
                message=f"Charitable contributions ({charitable_contributions:,.2f}) exceed 10% limitation ({charity_limit:,.2f})",
                rule="charitable_contributions_limit",
                current_value=charitable_contributions,
                expected_value=charity_limit
            ))
        
        # Either amount owed or overpayment should be > 0, not both
        amount_owed = self._get_decimal(form_data, 'tax_and_payments.line_35', 0)
        overpayment = self._get_decimal(form_data, 'tax_and_payments.line_36', 0)
        
        if amount_owed > 0 and overpayment > 0:
            results.append(ValidationResult(
                field="tax_and_payments.balance",
                severity=ValidationSeverity.ERROR,
                message="Cannot have both amount owed and overpayment greater than zero",
                rule="tax_balance_check"
            ))
        
        return results
    
    def _validate_m1_reconciliation(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Schedule M-1 reconciliation math"""
        results = []
        
        # Validate reconciliation calculation
        book_income = self._get_decimal(schedule_data, 'book_to_tax_additions.line_1', 0)
        total_additions = self._get_decimal(schedule_data, 'book_to_tax_additions.line_7', 0) 
        total_subtractions = self._get_decimal(schedule_data, 'tax_to_book_subtractions.line_11', 0)
        taxable_income = self._get_decimal(schedule_data, 'tax_to_book_subtractions.line_12', 0)
        
        expected_taxable_income = book_income + total_additions - total_subtractions
        
        if taxable_income != expected_taxable_income:
            results.append(ValidationResult(
                field="schedule_m1.line_12",
                severity=ValidationSeverity.ERROR,
                message=f"M-1 reconciliation calculation incorrect. Expected: {expected_taxable_income:,.2f}, Actual: {taxable_income:,.2f}",
                rule="m1_reconciliation_math",
                current_value=taxable_income,
                expected_value=expected_taxable_income
            ))
        
        return results
    
    def _validate_m2_rollforward(self, schedule_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Schedule M-2 retained earnings rollforward"""
        results = []
        
        beginning_balance = self._get_decimal(schedule_data, 'beginning_balance.line_1', 0)
        total_increases = self._get_decimal(schedule_data, 'additions_to_retained_earnings.line_4', 0)
        total_decreases = self._get_decimal(schedule_data, 'subtractions_from_retained_earnings.line_9', 0)
        ending_balance = self._get_decimal(schedule_data, 'ending_balance.line_10', 0)
        
        expected_ending_balance = beginning_balance + total_increases - total_decreases
        
        if ending_balance != expected_ending_balance:
            results.append(ValidationResult(
                field="schedule_m2.line_10",
                severity=ValidationSeverity.ERROR,
                message=f"M-2 rollforward calculation incorrect. Expected: {expected_ending_balance:,.2f}, Actual: {ending_balance:,.2f}",
                rule="m2_rollforward_math",
                current_value=ending_balance,
                expected_value=expected_ending_balance
            ))
        
        return results
    
    def _get_decimal(self, data: Dict[str, Any], path: str, default: float = 0) -> Decimal:
        """Get a decimal value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return Decimal(str(default))
        
        try:
            return Decimal(str(value)) if value is not None else Decimal(str(default))
        except (ValueError, TypeError):
            return Decimal(str(default))
    
    def _evaluate_calculation(self, calculation: str, data: Dict[str, Any]) -> Optional[Decimal]:
        """Safely evaluate calculation expressions"""
        # This is a simplified version - in production, use a proper expression parser
        # For now, handle simple additions and subtractions
        try:
            # Replace field names with values
            for field_name in data:
                if field_name in calculation:
                    field_value = self._get_decimal({'root': data}, f'root.{field_name}', 0)
                    calculation = calculation.replace(field_name, str(field_value))
            
            # Evaluate simple mathematical expressions
            # Note: In production, use a safe expression evaluator
            return Decimal(str(eval(calculation)))
        except:
            return None
    
    def generate_validation_report(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate a formatted validation report"""
        errors = [r for r in validation_results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in validation_results if r.severity == ValidationSeverity.WARNING]
        infos = [r for r in validation_results if r.severity == ValidationSeverity.INFO]
        
        return {
            "summary": {
                "total_issues": len(validation_results),
                "errors": len(errors),
                "warnings": len(warnings), 
                "infos": len(infos),
                "is_valid": len(errors) == 0
            },
            "errors": [self._format_result(r) for r in errors],
            "warnings": [self._format_result(r) for r in warnings],
            "infos": [self._format_result(r) for r in infos]
        }
    
    def _format_result(self, result: ValidationResult) -> Dict[str, Any]:
        """Format a validation result for display"""
        formatted = {
            "field": result.field,
            "message": result.message,
            "rule": result.rule,
            "severity": result.severity.value
        }
        
        if result.current_value is not None:
            formatted["current_value"] = str(result.current_value)
        if result.expected_value is not None:
            formatted["expected_value"] = str(result.expected_value)
            
        return formatted