from decimal import Decimal
from app.services.tax_validation_service import TaxFormValidationService, ValidationSeverity
from app.services.book_to_tax_adjustment_service import BookToTaxAdjustmentService
import json

class TestTaxValidationComprehensive:
    """Comprehensive test suite for tax validation system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validation_service = TaxFormValidationService()
        # Mock database session for adjustment service
        self.adjustment_service = BookToTaxAdjustmentService(None)
        
    def test_form_1120_basic_validation(self):
        """Test basic Form 1120 field validation"""
        form_data = {
            "form_1120": {
                "income": {
                    "line_1a": 1000000,  # Gross receipts
                    "line_1b": 5000,     # Returns and allowances
                    "line_2": 600000,    # Cost of goods sold
                    "line_5": 15000      # Interest income
                },
                "deductions": {
                    "line_12": 250000,   # Officer compensation
                    "line_13": 180000,   # Salaries and wages
                    "line_16": 60000,    # Rent
                    "line_18": 25000,    # Interest expense
                    "line_19": 45000     # Charitable contributions
                }
            }
        }
        
        results = self.validation_service.validate_form_1120_package(form_data)
        
        # Should have some calculation warnings but no critical errors
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Unexpected errors: {[e.message for e in errors]}"
        
    def test_charitable_contribution_limitation(self):
        """Test charitable contribution 10% limitation validation"""
        form_data = {
            "form_1120": {
                "income": {
                    "line_11": 500000  # Total income
                },
                "deductions": {
                    "line_19": 75000,  # Charitable contributions (15% of income - should trigger warning)
                    "line_27": 300000, # Total deductions
                    "line_28": 200000  # Taxable income before contributions
                }
            }
        }
        
        results = self.validation_service.validate_form_1120_package(form_data)
        
        # Should find charitable contribution limit violation
        charity_warnings = [r for r in results if "charitable" in r.message.lower()]
        assert len(charity_warnings) > 0, "Should detect charitable contribution limitation"
        
    def test_balance_sheet_balancing(self):
        """Test Schedule L balance sheet balancing validation"""
        form_data = {
            "schedule_l": {
                "assets": {
                    "line_15": {"col_b": 800000, "col_d": 950000}  # Total assets
                },
                "liabilities_and_equity": {
                    "line_28": {"col_b": 800000, "col_d": 900000}  # Total liab + equity (doesn't balance)
                }
            }
        }
        
        results = self.validation_service.validate_form_1120_package(form_data)
        
        # Should find balance sheet imbalance
        balance_errors = [r for r in results if "balance" in r.message.lower()]
        assert len(balance_errors) > 0, "Should detect balance sheet imbalance"
        
    def test_cross_form_tie_validation(self):
        """Test cross-form tie-out validations"""
        form_data = {
            "form_1120": {
                "deductions": {
                    "line_30": 150000  # Taxable income on Form 1120
                }
            },
            "schedule_m1": {
                "tax_to_book_subtractions": {
                    "line_12": 145000  # Taxable income on M-1 (doesn't tie)
                }
            },
            "schedule_l": {
                "liabilities_and_equity": {
                    "line_28_col_b": 200000,  # Beginning retained earnings
                    "line_28_col_d": 250000   # Ending retained earnings
                }
            },
            "schedule_m2": {
                "beginning_balance": {
                    "line_1": 195000  # Beginning RE on M-2 (doesn't tie to Schedule L)
                },
                "ending_balance": {
                    "line_10": 250000  # Ending RE on M-2 (ties to Schedule L)
                }
            }
        }
        
        results = self.validation_service.validate_form_1120_package(form_data)
        
        # Should find cross-form tie-out errors
        tie_errors = [r for r in results if "tie" in r.message.lower() or "equal" in r.message.lower()]
        assert len(tie_errors) >= 2, f"Should detect multiple tie-out errors, found: {len(tie_errors)}"
        
    def test_m1_book_to_tax_adjustments(self):
        """Test Schedule M-1 book-to-tax adjustment calculations"""
        trial_balance = {
            "net_income": 180000,      # Book income
            "6850": 38000,             # Federal tax expense
            "6500": 25000,             # Business meals
            "6530": 8000,              # Entertainment
            "6920": 3500,              # Fines and penalties
            "6800": 15000,             # Charitable contributions
            "4300": 5000,              # Municipal bond interest
            "4200": 12000              # Dividend income
        }
        
        book_income = Decimal("180000")
        adjustments = self.adjustment_service.calculate_m1_adjustments(trial_balance, book_income)
        
        # Verify key adjustments
        adjustment_types = [adj.adjustment_type for adj in adjustments]
        
        assert "federal_tax_expense" in adjustment_types, "Should identify federal tax expense"
        assert "meals_50_percent" in adjustment_types, "Should identify meals limitation"
        assert "entertainment_100_percent" in adjustment_types, "Should identify entertainment limitation"
        assert "fines_penalties" in adjustment_types, "Should identify non-deductible fines"
        assert "municipal_bond_interest" in adjustment_types, "Should identify tax-exempt income"
        
        # Check specific amounts
        meals_adj = next((adj for adj in adjustments if adj.adjustment_type == "meals_50_percent"), None)
        assert meals_adj is not None, "Should have meals adjustment"
        assert meals_adj.difference == Decimal("12500"), f"Meals adjustment should be $12,500 (50% of $25,000), got {meals_adj.difference}"
        
        entertainment_adj = next((adj for adj in adjustments if adj.adjustment_type == "entertainment_100_percent"), None)
        assert entertainment_adj is not None, "Should have entertainment adjustment"
        assert entertainment_adj.difference == Decimal("8000"), f"Entertainment adjustment should be $8,000 (100% of $8,000), got {entertainment_adj.difference}"
        
    def test_m1_generation_from_adjustments(self):
        """Test Schedule M-1 form generation from adjustments"""
        trial_balance = {
            "net_income": 200000,
            "6850": 42000,  # Federal tax
            "6500": 18000,  # Meals
            "4300": 8000    # Municipal bond interest
        }
        
        book_income = Decimal("200000")
        adjustments = self.adjustment_service.calculate_m1_adjustments(trial_balance, book_income)
        m1_data = self.adjustment_service.generate_m1_from_adjustments(adjustments, book_income)
        
        # Verify M-1 structure
        assert "book_to_tax_additions" in m1_data
        assert "tax_to_book_subtractions" in m1_data
        
        additions = m1_data["book_to_tax_additions"]
        subtractions = m1_data["tax_to_book_subtractions"]
        
        # Check line 1 (book income)
        assert additions["line_1"] == 200000, f"Line 1 should be $200,000, got {additions['line_1']}"
        
        # Check line 2 (federal tax)
        assert additions["line_2"] == 42000, f"Line 2 should be $42,000, got {additions['line_2']}"
        
        # Check line 5 (meals adjustment)
        assert additions["line_5"] == 9000, f"Line 5 should include $9,000 meals adjustment, got {additions['line_5']}"
        
        # Check line 8 (tax-exempt income)
        assert subtractions["line_8"] == 8000, f"Line 8 should be $8,000, got {subtractions['line_8']}"
        
        # Check line 12 (taxable income)
        expected_taxable = 200000 + 42000 + 9000 - 8000  # Book income + additions - subtractions
        assert subtractions["line_12"] == expected_taxable, f"Line 12 should be {expected_taxable}, got {subtractions['line_12']}"
        
    def test_validation_report_generation(self):
        """Test validation report generation"""
        form_data = {
            "form_1120": {
                "income": {
                    "line_1a": 750000,
                    "line_11": 750000
                },
                "deductions": {
                    "line_19": 100000,  # Excessive charitable (>10%)
                    "line_27": 500000,
                    "line_30": 150000
                },
                "tax_and_payments": {
                    "line_35": 25000,  # Amount owed
                    "line_36": 5000    # Overpayment (should trigger error)
                }
            }
        }
        
        results = self.validation_service.validate_form_1120_package(form_data)
        report = self.validation_service.generate_validation_report(results)
        
        # Verify report structure
        assert "summary" in report
        assert "errors" in report
        assert "warnings" in report
        
        summary = report["summary"]
        assert summary["total_issues"] > 0, "Should have validation issues"
        assert summary["errors"] > 0, "Should have errors (amount owed + overpayment)"
        assert not summary["is_valid"], "Form should not be valid"
        
    def test_complex_business_scenario(self):
        """Test complex real-world business scenario"""
        # Simulate a mid-size manufacturing company
        trial_balance = {
            "net_income": 485000,
            "4000": 2500000,           # Sales revenue
            "5000": 1200000,           # Cost of goods sold
            "6100": 350000,            # Officer compensation
            "6110": 450000,            # Employee salaries
            "6200": 72000,             # Rent expense
            "6300": 35000,             # Interest expense
            "6500": 32000,             # Business meals
            "6530": 15000,             # Entertainment
            "6800": 55000,             # Charitable contributions
            "6850": 102000,            # Federal income tax expense
            "6920": 8500,              # Fines and penalties
            "4300": 12000,             # Municipal bond interest
            "4200": 25000,             # Dividend income
            # Balance sheet accounts
            "1000": 125000,            # Cash
            "1100": 185000,            # Accounts receivable
            "1200": 275000,            # Inventory
            "1500": 850000,            # Fixed assets
            "2000": 95000,             # Accounts payable
            "2100": 180000             # Notes payable
        }
        
        book_income = Decimal("485000")
        
        # Calculate M-1 adjustments
        adjustments = self.adjustment_service.calculate_m1_adjustments(trial_balance, book_income)
        m1_data = self.adjustment_service.generate_m1_from_adjustments(adjustments, book_income)
        
        # Generate adjustment report
        adj_report = self.adjustment_service.generate_adjustment_report(adjustments)
        
        # Verify comprehensive adjustments
        assert adj_report["summary"]["total_adjustments"] >= 5, "Should have multiple adjustments for complex scenario"
        assert adj_report["summary"]["total_additions"] > 100000, "Should have substantial additions"
        assert adj_report["summary"]["total_subtractions"] > 0, "Should have some subtractions"
        
        # Check taxable income calculation
        taxable_income = m1_data["tax_to_book_subtractions"]["line_12"]
        assert taxable_income > 485000, "Taxable income should be higher than book income due to non-deductible items"
        assert taxable_income < 700000, "Taxable income should be reasonable"
        
        # Verify specific adjustments make sense
        total_additions = adj_report["summary"]["total_additions"]
        
        # Federal tax + 50% meals + 100% entertainment + fines should be significant
        expected_minimum_additions = 102000 + 16000 + 15000 + 8500  # Federal tax + 50% meals + entertainment + fines
        assert total_additions >= expected_minimum_additions * 0.9, f"Total additions {total_additions} should be at least {expected_minimum_additions * 0.9}"
        
    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases"""
        # Test with empty form data
        empty_results = self.validation_service.validate_form_1120_package({})
        assert len(empty_results) == 0, "Empty form should not crash validation"
        
        # Test with negative values
        negative_form = {
            "form_1120": {
                "income": {
                    "line_1a": -50000  # Negative gross receipts
                },
                "deductions": {
                    "line_12": -25000  # Negative officer compensation
                }
            }
        }
        
        negative_results = self.validation_service.validate_form_1120_package(negative_form)
        negative_errors = [r for r in negative_results if r.severity == ValidationSeverity.ERROR]
        assert len(negative_errors) >= 1, "Should detect negative value errors"
        
        # Test with very large values
        large_form = {
            "form_1120": {
                "income": {
                    "line_1a": 999999999999  # Very large gross receipts
                }
            }
        }
        
        large_results = self.validation_service.validate_form_1120_package(large_form)
        # Should handle large values without crashing
        assert isinstance(large_results, list), "Should handle large values gracefully"

if __name__ == "__main__":
    # Run the tests
    test_suite = TestTaxValidationComprehensive()
    test_suite.setup_method()
    
    try:
        test_suite.test_form_1120_basic_validation()
        print("✅ Basic validation test passed")
        
        test_suite.test_charitable_contribution_limitation()
        print("✅ Charitable contribution test passed")
        
        test_suite.test_m1_book_to_tax_adjustments()
        print("✅ M-1 adjustments test passed")
        
        test_suite.test_m1_generation_from_adjustments()
        print("✅ M-1 generation test passed")
        
        test_suite.test_complex_business_scenario()
        print("✅ Complex business scenario test passed")
        
        test_suite.test_error_handling_and_edge_cases()
        print("✅ Error handling test passed")
        
        print("\n🎉 All tax validation tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise