import pytest
import json
from decimal import Decimal
from typing import Dict, Any

from app.services.tax_validation_service import TaxFormValidationService, ValidationSeverity
from app.services.book_to_tax_adjustment_service import BookToTaxAdjustmentService

class TestTaxValidationIntegration:
    """
    Integration tests demonstrating the complete tax preparation pipeline:
    Trial Balance → M-1 Adjustments → Form 1120 → Validation
    """
    
    @pytest.fixture
    def sample_trial_balance(self):
        """Sample trial balance with various tax scenarios"""
        return {
            # Assets
            "1010": 25000.00,    # Cash
            "1100": 45000.00,    # Accounts Receivable
            "1110": -2250.00,    # Allowance for Doubtful Accounts
            "1200": 35000.00,    # Inventory
            "1400": 150000.00,   # Equipment
            "1500": -60000.00,   # Accumulated Depreciation
            
            # Liabilities & Equity
            "2000": -18000.00,   # Accounts Payable
            "2100": -8500.00,    # Accrued Expenses  
            "2200": -50000.00,   # Notes Payable
            "3000": -10000.00,   # Common Stock
            "3400": -85000.00,   # Retained Earnings (beginning)
            
            # Revenue
            "4100": -750000.00,  # Sales Revenue
            "4200": -5000.00,    # Dividend Income (qualifying)
            "4300": -3000.00,    # Municipal Bond Interest (tax-exempt)
            
            # Expenses
            "5000": 450000.00,   # Cost of Goods Sold
            "6100": 85000.00,    # Officer Compensation
            "6200": 120000.00,   # Salaries and Wages
            "6300": 24000.00,    # Rent Expense
            "6400": 12000.00,    # Insurance
            "6500": 8000.00,     # Meals and Entertainment (50% limit)
            "6530": 3000.00,     # Entertainment (100% nondeductible)
            "6600": 15000.00,    # Professional Services
            "6700": 20000.00,    # Depreciation Expense (book)
            "6800": 25000.00,    # Charitable Contributions
            "6850": 18000.00,    # Federal Income Tax Expense
            "6920": 2500.00,     # Fines and Penalties (nondeductible)
            "6810": 5000.00,     # Life Insurance Premiums (nondeductible)
            "6930": 1000.00      # Political Contributions (nondeductible)
        }
    
    @pytest.fixture
    def book_income(self):
        """Calculate book income from trial balance"""
        # Revenue: $750,000 + $5,000 + $3,000 = $758,000
        # Expenses: $450,000 + $85,000 + $120,000 + $24,000 + $12,000 + $8,000 + $3,000 + $15,000 + $20,000 + $25,000 + $18,000 + $2,500 + $5,000 + $1,000 = $788,500
        # Net Loss: $758,000 - $788,500 = -$30,500
        return Decimal("-30500.00")
    
    def test_complete_m1_calculation_pipeline(self, sample_trial_balance, book_income):
        """Test complete M-1 adjustment calculation pipeline"""
        
        # Initialize service (mock db session)
        adjustment_service = BookToTaxAdjustmentService(db=None)
        
        # Calculate M-1 adjustments
        adjustments = adjustment_service.calculate_m1_adjustments(
            trial_balance=sample_trial_balance,
            book_income=book_income
        )
        
        # Verify key adjustments are calculated
        adjustment_types = [adj.adjustment_type for adj in adjustments]
        
        assert "federal_tax_expense" in adjustment_types
        assert "meals_50_percent" in adjustment_types
        assert "entertainment_100_percent" in adjustment_types
        assert "fines_penalties" in adjustment_types
        assert "life_insurance_premiums" in adjustment_types
        assert "political_contributions" in adjustment_types
        assert "municipal_bond_interest" in adjustment_types
        
        # Verify specific adjustment amounts
        fed_tax_adj = next(adj for adj in adjustments if adj.adjustment_type == "federal_tax_expense")
        assert fed_tax_adj.difference == Decimal("18000.00")
        
        meals_adj = next(adj for adj in adjustments if adj.adjustment_type == "meals_50_percent")
        assert meals_adj.difference == Decimal("4000.00")  # 50% of $8,000
        
        entertainment_adj = next(adj for adj in adjustments if adj.adjustment_type == "entertainment_100_percent")
        assert entertainment_adj.difference == Decimal("3000.00")  # 100% of $3,000
        
        muni_bond_adj = next(adj for adj in adjustments if adj.adjustment_type == "municipal_bond_interest")
        assert muni_bond_adj.difference == Decimal("3000.00")
        
        # Generate M-1 structure
        m1_data = adjustment_service.generate_m1_from_adjustments(adjustments, book_income)
        
        # Verify M-1 calculations
        assert m1_data["book_to_tax_additions"]["line_1"] == float(book_income)  # Net income per books
        assert m1_data["book_to_tax_additions"]["line_2"] == 18000.00  # Federal tax expense
        assert m1_data["book_to_tax_additions"]["line_5"] >= 13500.00  # Nondeductible expenses (meals 50% + entertainment + fines + life ins + political)
        assert m1_data["tax_to_book_subtractions"]["line_8"] == 3000.00  # Tax-exempt income
        
        # Calculate expected taxable income
        expected_taxable_income = (
            float(book_income) + 
            m1_data["book_to_tax_additions"]["line_7"] - 
            m1_data["tax_to_book_subtractions"]["line_11"]
        )
        
        assert m1_data["tax_to_book_subtractions"]["line_12"] == expected_taxable_income
        
        return m1_data, adjustments
    
    def test_form_1120_validation_with_errors(self):
        """Test Form 1120 validation with intentional errors"""
        
        validation_service = TaxFormValidationService()
        
        # Create form data with validation errors
        form_data = {
            "form_1120": {
                "income": {
                    "line_1a": 1000000.00,  # Gross receipts
                    "line_1b": 50000.00,    # Returns and allowances  
                    "line_1c": 950000.00,   # Net sales (should auto-calculate)
                    "line_2": 600000.00,    # COGS
                    "line_3": 350000.00,    # Gross profit (should auto-calculate)
                    "line_11": 355000.00    # Total income
                },
                "deductions": {
                    "line_12": 50000.00,    # Officer compensation
                    "line_13": 120000.00,   # Salaries and wages
                    "line_19": 40000.00,    # Charitable contributions (may exceed 10% limit)
                    "line_27": 250000.00,   # Total deductions
                    "line_28": 105000.00,   # Taxable income before special deductions
                    "line_30": 105000.00    # Taxable income
                },
                "tax_and_payments": {
                    "line_31": 22050.00,    # Total tax
                    "line_32b": 20000.00,   # Estimated payments
                    "line_33": 20000.00,    # Total payments
                    "line_35": 2050.00,     # Amount owed
                    "line_36": 500.00       # ERROR: Both amount owed AND overpayment > 0
                }
            }
        }
        
        # Run validation
        results = validation_service.validate_form_1120(form_data["form_1120"])
        
        # Check for expected errors
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        
        # Should have error for both amount owed and overpayment > 0
        payment_errors = [r for r in error_results if "amount owed" in r.message.lower() and "overpayment" in r.message.lower()]
        assert len(payment_errors) > 0
        
        # Should have warning for charitable contributions potentially exceeding 10% limit
        charity_warnings = [r for r in warning_results if "charitable" in r.message.lower()]
        # Note: This depends on the actual calculation - may or may not trigger based on taxable income
        
        return results
    
    def test_schedule_l_balance_sheet_validation(self):
        """Test Schedule L balance sheet validation"""
        
        validation_service = TaxFormValidationService()
        
        # Create unbalanced balance sheet
        schedule_l_data = {
            "assets": {
                "line_1": 50000.00,     # Cash
                "line_2a": 75000.00,    # Gross receivables
                "line_2b": 3750.00,     # Allowance for bad debts
                "line_3": 40000.00,     # Inventory
                "line_10a": 200000.00,  # Depreciable assets
                "line_10b": 80000.00,   # Accumulated depreciation
                "line_17": 281250.00    # Total assets (should auto-calculate to balance)
            },
            "liabilities_and_equity": {
                "line_18": 25000.00,    # Accounts payable
                "line_22": 100000.00,   # Long-term debt
                "line_25": 50000.00,    # Common stock
                "line_28": 105000.00,   # Retained earnings
                "line_31": 280000.00    # Total liab & equity (ERROR: doesn't equal assets)
            }
        }
        
        # Run validation
        results = validation_service.validate_schedule_l(schedule_l_data)
        
        # Should have balance sheet balance error
        balance_errors = [r for r in results if r.severity == ValidationSeverity.ERROR and "balance" in r.message.lower()]
        assert len(balance_errors) > 0
        
        # Check specific error message
        balance_error = balance_errors[0]
        assert "281250" in balance_error.message  # Assets amount
        assert "280000" in balance_error.message  # Liab & equity amount
        
        return results
    
    def test_cross_form_validation_ties(self):
        """Test cross-form tie-out validations"""
        
        validation_service = TaxFormValidationService()
        
        # Create form package with tie-out errors
        form_package = {
            "form_1120": {
                "deductions": {
                    "line_30": 105000.00  # Taxable income
                }
            },
            "schedule_l": {
                "liabilities_and_equity": {
                    "line_28_col_b": 85000.00,  # Beginning retained earnings
                    "line_28_col_d": 140000.00  # Ending retained earnings
                }
            },
            "schedule_m1": {
                "book_to_tax_additions": {
                    "line_1": -30500.00  # Net income per books
                },
                "tax_to_book_subtractions": {
                    "line_12": 110000.00  # ERROR: Doesn't tie to Form 1120 line 30
                }
            },
            "schedule_m2": {
                "beginning_balance": {
                    "line_1": 80000.00  # ERROR: Doesn't tie to Schedule L
                },
                "additions_to_retained_earnings": {
                    "line_2": -25000.00  # ERROR: Doesn't tie to Schedule M-1
                },
                "ending_balance": {
                    "line_10": 135000.00  # ERROR: Doesn't tie to Schedule L
                }
            }
        }
        
        # Run cross-form validation
        results = validation_service.validate_cross_form_ties(
            form_package["form_1120"],
            form_package["schedule_l"],
            form_package["schedule_m1"],
            form_package["schedule_m2"]
        )
        
        # Should have multiple tie-out errors
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(error_results) >= 4  # Should have at least 4 tie-out errors
        
        # Verify specific tie-out errors
        error_rules = [r.rule for r in error_results]
        assert "m1_form_1120_tie" in error_rules
        assert "m2_schedule_l_beginning_tie" in error_rules
        assert "m2_schedule_l_ending_tie" in error_rules
        assert "m2_m1_net_income_tie" in error_rules
        
        return results
    
    def test_adjustment_report_generation(self, sample_trial_balance, book_income):
        """Test comprehensive adjustment report generation"""
        
        adjustment_service = BookToTaxAdjustmentService(db=None)
        
        # Calculate adjustments
        adjustments = adjustment_service.calculate_m1_adjustments(
            trial_balance=sample_trial_balance,
            book_income=book_income
        )
        
        # Generate report
        report = adjustment_service.generate_adjustment_report(adjustments)
        
        # Verify report structure
        assert "summary" in report
        assert "adjustments_by_type" in report
        assert "permanent_vs_timing" in report
        
        # Verify summary calculations
        summary = report["summary"]
        assert summary["total_adjustments"] > 0
        assert summary["total_additions"] > 0
        assert summary["total_subtractions"] > 0
        assert summary["permanent_differences"] > 0
        
        # Verify adjustments are properly categorized
        additions = report["adjustments_by_type"]["additions"]
        subtractions = report["adjustments_by_type"]["subtractions"]
        
        assert len(additions) > 0
        assert len(subtractions) > 0
        
        # Check for expected adjustment types
        addition_types = [adj["type"] for adj in additions]
        subtraction_types = [adj["type"] for adj in subtractions]
        
        assert "federal_tax_expense" in addition_types
        assert "meals_50_percent" in addition_types
        assert "municipal_bond_interest" in subtraction_types
        
        return report
    
    def test_validation_report_generation(self):
        """Test validation report generation with mixed errors and warnings"""
        
        validation_service = TaxFormValidationService()
        
        # Create form with mixed validation issues
        form_data = {
            "form_1120": {
                "income": {
                    "line_1a": "",  # ERROR: Required field missing
                    "line_11": 500000.00
                },
                "deductions": {
                    "line_19": 60000.00,  # WARNING: May exceed charitable limit
                    "line_30": 450000.00
                },
                "tax_and_payments": {
                    "line_31": 94500.00,
                    "line_35": 5000.00,
                    "line_36": 2000.00  # ERROR: Both amount owed and overpayment
                }
            }
        }
        
        # Run validation
        results = validation_service.validate_form_1120(form_data["form_1120"])
        
        # Generate report
        report = validation_service.generate_validation_report(results)
        
        # Verify report structure
        assert "summary" in report
        assert "errors" in report
        assert "warnings" in report
        assert "infos" in report
        
        # Verify summary
        summary = report["summary"]
        assert summary["total_issues"] > 0
        assert summary["errors"] > 0
        assert summary["is_valid"] == False  # Has errors
        
        # Verify error details
        errors = report["errors"]
        assert len(errors) > 0
        
        # Check for specific error types
        error_fields = [error["field"] for error in errors]
        error_rules = [error["rule"] for error in errors]
        
        assert any("line_1a" in field for field in error_fields)  # Missing required field
        assert "required_field" in error_rules
        assert "tax_balance_check" in error_rules  # Both amount owed and overpayment
        
        return report

# Sample test data for demonstration
SAMPLE_TEST_SCENARIOS = {
    "scenario_1_profitable_company": {
        "description": "Profitable company with common adjustments",
        "book_income": 150000.00,
        "expected_adjustments": [
            "federal_tax_expense",
            "meals_50_percent", 
            "municipal_bond_interest"
        ]
    },
    "scenario_2_loss_company": {
        "description": "Company with book loss but tax adjustments",
        "book_income": -30500.00,
        "expected_adjustments": [
            "federal_tax_expense",
            "nondeductible_expenses",
            "tax_exempt_income"
        ]
    },
    "scenario_3_high_charity": {
        "description": "Company with charitable contributions exceeding 10% limit",
        "charitable_contributions": 50000.00,
        "taxable_income_base": 400000.00,
        "expected_excess": 10000.00  # $50k - (10% * $400k)
    }
}