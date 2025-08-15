from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum
import re
from sqlalchemy.orm import Session

@dataclass
class TaxAdjustment:
    adjustment_type: str
    description: str
    book_amount: Decimal
    tax_amount: Decimal
    difference: Decimal
    m1_line: str
    explanation: str
    permanent: bool = True  # True for permanent differences, False for timing differences

class AdjustmentType(Enum):
    # M-1 Additions (increase taxable income)
    FEDERAL_TAX_EXPENSE = "federal_tax_expense"
    MEALS_50_PERCENT = "meals_50_percent"
    ENTERTAINMENT_100_PERCENT = "entertainment_100_percent"
    FINES_PENALTIES = "fines_penalties"
    LIFE_INSURANCE_PREMIUMS = "life_insurance_premiums"
    POLITICAL_CONTRIBUTIONS = "political_contributions"
    EXCESS_CHARITABLE = "excess_charitable"
    DEPRECIATION_BOOK_OVER_TAX = "depreciation_book_over_tax"
    
    # M-1 Subtractions (decrease taxable income)
    MUNICIPAL_BOND_INTEREST = "municipal_bond_interest"
    LIFE_INSURANCE_PROCEEDS = "life_insurance_proceeds"
    DEPRECIATION_TAX_OVER_BOOK = "depreciation_tax_over_book"
    DIVIDENDS_RECEIVED_DEDUCTION = "dividends_received_deduction"
    
class BookToTaxAdjustmentService:
    """
    Automated book-to-tax adjustment calculation engine.
    Analyzes Trial Balance and generates Schedule M-1 adjustments.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    def calculate_m1_adjustments(self, 
                                trial_balance: Dict[str, Any], 
                                book_income: Decimal,
                                entity_info: Dict[str, Any] = None) -> List[TaxAdjustment]:
        """
        Calculate all Schedule M-1 adjustments from trial balance data.
        
        Args:
            trial_balance: Dict with account codes as keys and balances as values
            book_income: Net income per books (starting point for M-1)
            entity_info: Additional entity information for specific calculations
            
        Returns:
            List of TaxAdjustment objects for Schedule M-1
        """
        adjustments = []
        
        # M-1 Additions (Lines 2-6)
        adjustments.extend(self._calculate_federal_tax_expense(trial_balance))
        adjustments.extend(self._calculate_meals_entertainment_limitation(trial_balance))
        adjustments.extend(self._calculate_nondeductible_expenses(trial_balance))
        adjustments.extend(self._calculate_depreciation_differences(trial_balance, 'book_over_tax'))
        adjustments.extend(self._calculate_excess_charitable_contributions(trial_balance, book_income))
        
        # M-1 Subtractions (Lines 8-10)
        adjustments.extend(self._calculate_tax_exempt_income(trial_balance))
        adjustments.extend(self._calculate_dividends_received_deduction(trial_balance))
        adjustments.extend(self._calculate_depreciation_differences(trial_balance, 'tax_over_book'))
        
        return adjustments
    
    def _calculate_federal_tax_expense(self, trial_balance: Dict[str, Any]) -> List[TaxAdjustment]:
        """Calculate federal income tax expense adjustment (M-1 Line 2)"""
        adjustments = []
        
        # Look for federal income tax expense accounts
        fed_tax_accounts = ['6850', '6851', '7850']  # Common federal tax expense account codes
        total_fed_tax = Decimal('0')
        
        for account_code in fed_tax_accounts:
            if account_code in trial_balance:
                total_fed_tax += Decimal(str(trial_balance[account_code]))
        
        if total_fed_tax > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.FEDERAL_TAX_EXPENSE.value,
                description="Federal income tax per books",
                book_amount=total_fed_tax,
                tax_amount=Decimal('0'),  # Not deductible for tax
                difference=total_fed_tax,
                m1_line="line_2",
                explanation="Federal income tax expense recorded in books but not deductible for tax purposes",
                permanent=True
            ))
        
        return adjustments
    
    def _calculate_meals_entertainment_limitation(self, trial_balance: Dict[str, Any]) -> List[TaxAdjustment]:
        """Calculate 50% meals and 100% entertainment limitation (M-1 Line 5)"""
        adjustments = []
        
        # Meals accounts (50% limitation)
        meals_accounts = ['6500', '6510', '6520']  # Meals, business meals, etc.
        total_meals = Decimal('0')
        
        for account_code in meals_accounts:
            if account_code in trial_balance:
                total_meals += Decimal(str(trial_balance[account_code]))
        
        if total_meals > 0:
            nondeductible_meals = total_meals * Decimal('0.50')
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.MEALS_50_PERCENT.value,
                description="50% limitation on meals",
                book_amount=total_meals,
                tax_amount=total_meals - nondeductible_meals,
                difference=nondeductible_meals,
                m1_line="line_5",
                explanation=f"50% of business meals ({total_meals:,.2f}) not deductible = {nondeductible_meals:,.2f}",
                permanent=True
            ))
        
        # Entertainment accounts (100% non-deductible)
        entertainment_accounts = ['6530', '6540']  # Entertainment, client entertainment
        total_entertainment = Decimal('0')
        
        for account_code in entertainment_accounts:
            if account_code in trial_balance:
                total_entertainment += Decimal(str(trial_balance[account_code]))
        
        if total_entertainment > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.ENTERTAINMENT_100_PERCENT.value,
                description="100% limitation on entertainment",
                book_amount=total_entertainment,
                tax_amount=Decimal('0'),
                difference=total_entertainment,
                m1_line="line_5",
                explanation=f"Entertainment expenses ({total_entertainment:,.2f}) are 100% non-deductible",
                permanent=True
            ))
        
        return adjustments
    
    def _calculate_nondeductible_expenses(self, trial_balance: Dict[str, Any]) -> List[TaxAdjustment]:
        """Calculate various non-deductible expenses (M-1 Line 5)"""
        adjustments = []
        
        # Fines and penalties
        fines_accounts = ['6920', '6925']
        total_fines = Decimal('0')
        
        for account_code in fines_accounts:
            if account_code in trial_balance:
                total_fines += Decimal(str(trial_balance[account_code]))
        
        if total_fines > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.FINES_PENALTIES.value,
                description="Fines and penalties",
                book_amount=total_fines,
                tax_amount=Decimal('0'),
                difference=total_fines,
                m1_line="line_5",
                explanation=f"Fines and penalties ({total_fines:,.2f}) are not deductible",
                permanent=True
            ))
        
        # Life insurance premiums (officer/key employee)
        life_insurance_accounts = ['6810', '6815']
        total_life_insurance = Decimal('0')
        
        for account_code in life_insurance_accounts:
            if account_code in trial_balance:
                total_life_insurance += Decimal(str(trial_balance[account_code]))
        
        if total_life_insurance > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.LIFE_INSURANCE_PREMIUMS.value,
                description="Life insurance premiums (officer/key employee)",
                book_amount=total_life_insurance,
                tax_amount=Decimal('0'),
                difference=total_life_insurance,
                m1_line="line_5",
                explanation=f"Life insurance premiums ({total_life_insurance:,.2f}) on officers/key employees not deductible",
                permanent=True
            ))
        
        # Political contributions
        political_accounts = ['6930', '6935']
        total_political = Decimal('0')
        
        for account_code in political_accounts:
            if account_code in trial_balance:
                total_political += Decimal(str(trial_balance[account_code]))
        
        if total_political > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.POLITICAL_CONTRIBUTIONS.value,
                description="Political contributions",
                book_amount=total_political,
                tax_amount=Decimal('0'),
                difference=total_political,
                m1_line="line_5",
                explanation=f"Political contributions ({total_political:,.2f}) are not deductible",
                permanent=True
            ))
        
        return adjustments
    
    def _calculate_excess_charitable_contributions(self, trial_balance: Dict[str, Any], book_income: Decimal) -> List[TaxAdjustment]:
        """Calculate excess charitable contributions over 10% limitation (M-1 Line 5)"""
        adjustments = []
        
        # Charitable contribution accounts
        charity_accounts = ['6800', '6805']
        total_charity = Decimal('0')
        
        for account_code in charity_accounts:
            if account_code in trial_balance:
                total_charity += Decimal(str(trial_balance[account_code]))
        
        if total_charity > 0:
            # Calculate 10% limitation base (taxable income before charitable contributions)
            # Approximate using book income for simplicity
            taxable_income_base = book_income + total_charity  # Add back charity to get base
            charity_limit = taxable_income_base * Decimal('0.10')
            excess_charity = max(Decimal('0'), total_charity - charity_limit)
            
            if excess_charity > 0:
                adjustments.append(TaxAdjustment(
                    adjustment_type=AdjustmentType.EXCESS_CHARITABLE.value,
                    description="Excess charitable contributions over 10% limit",
                    book_amount=total_charity,
                    tax_amount=charity_limit,
                    difference=excess_charity,
                    m1_line="line_5",
                    explanation=f"Charitable contributions ({total_charity:,.2f}) exceed 10% limit ({charity_limit:,.2f}). Excess: {excess_charity:,.2f}",
                    permanent=False  # Can carry forward 5 years
                ))
        
        return adjustments
    
    def _calculate_tax_exempt_income(self, trial_balance: Dict[str, Any]) -> List[TaxAdjustment]:
        """Calculate tax-exempt income (M-1 Line 8)"""
        adjustments = []
        
        # Municipal bond interest
        muni_bond_accounts = ['4300', '4310']
        total_muni_interest = Decimal('0')
        
        for account_code in muni_bond_accounts:
            if account_code in trial_balance:
                total_muni_interest += Decimal(str(trial_balance[account_code]))
        
        if total_muni_interest > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.MUNICIPAL_BOND_INTEREST.value,
                description="Tax-exempt municipal bond interest",
                book_amount=total_muni_interest,
                tax_amount=Decimal('0'),
                difference=total_muni_interest,
                m1_line="line_8",
                explanation=f"Municipal bond interest ({total_muni_interest:,.2f}) is tax-exempt",
                permanent=True
            ))
        
        # Life insurance proceeds
        life_proceeds_accounts = ['4400', '4410']
        total_life_proceeds = Decimal('0')
        
        for account_code in life_proceeds_accounts:
            if account_code in trial_balance:
                total_life_proceeds += Decimal(str(trial_balance[account_code]))
        
        if total_life_proceeds > 0:
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.LIFE_INSURANCE_PROCEEDS.value,
                description="Life insurance proceeds",
                book_amount=total_life_proceeds,
                tax_amount=Decimal('0'),
                difference=total_life_proceeds,
                m1_line="line_8",
                explanation=f"Life insurance proceeds ({total_life_proceeds:,.2f}) are not taxable",
                permanent=True
            ))
        
        return adjustments
    
    def _calculate_dividends_received_deduction(self, trial_balance: Dict[str, Any]) -> List[TaxAdjustment]:
        """Calculate dividends received deduction (M-1 Line 9)"""
        adjustments = []
        
        # Dividend income accounts
        dividend_accounts = ['4200', '4210']
        total_dividends = Decimal('0')
        
        for account_code in dividend_accounts:
            if account_code in trial_balance:
                total_dividends += Decimal(str(trial_balance[account_code]))
        
        if total_dividends > 0:
            # Assume 70% deduction for simplicity (actual calculation depends on ownership percentage)
            # 70% for <20% ownership, 80% for 20-80% ownership, 100% for >80% ownership
            drd_percentage = Decimal('0.70')  # Conservative assumption
            drd_amount = total_dividends * drd_percentage
            
            adjustments.append(TaxAdjustment(
                adjustment_type=AdjustmentType.DIVIDENDS_RECEIVED_DEDUCTION.value,
                description="Dividends received deduction",
                book_amount=total_dividends,
                tax_amount=total_dividends - drd_amount,
                difference=drd_amount,
                m1_line="line_9",
                explanation=f"Dividends received deduction ({drd_percentage:.0%} of {total_dividends:,.2f}) = {drd_amount:,.2f}",
                permanent=True
            ))
        
        return adjustments
    
    def _calculate_depreciation_differences(self, trial_balance: Dict[str, Any], direction: str) -> List[TaxAdjustment]:
        """Calculate depreciation differences between book and tax"""
        adjustments = []
        
        # This would typically require additional data about book vs tax depreciation
        # For now, return empty list - would need integration with fixed asset system
        # In production, this would:
        # 1. Compare book depreciation expense to tax depreciation (Form 4562)
        # 2. Calculate the difference
        # 3. Determine if book > tax (M-1 addition) or tax > book (M-1 subtraction)
        
        return adjustments
    
    def generate_m1_from_adjustments(self, adjustments: List[TaxAdjustment], book_income: Decimal) -> Dict[str, Any]:
        """Generate Schedule M-1 data structure from adjustments"""
        
        # Initialize M-1 structure
        m1_data = {
            "book_to_tax_additions": {
                "line_1": float(book_income),  # Net income per books
                "line_2": 0,  # Federal income tax per books
                "line_3": 0,  # Excess capital losses
                "line_4": 0,  # Income subject to tax not recorded on books
                "line_5": 0,  # Expenses recorded on books not deducted on return
                "line_6": 0,  # Other additions
                "line_7": 0   # Total additions (auto-calculated)
            },
            "tax_to_book_subtractions": {
                "line_8": 0,  # Income recorded on books not included on return
                "line_9": 0,  # Deductions on return not charged against book income
                "line_10": 0, # Other subtractions
                "line_11": 0, # Total subtractions (auto-calculated)
                "line_12": 0  # Income per return (auto-calculated)
            }
        }
        
        # Populate adjustments
        for adjustment in adjustments:
            if adjustment.m1_line == "line_2":
                m1_data["book_to_tax_additions"]["line_2"] += float(adjustment.difference)
            elif adjustment.m1_line == "line_5":
                m1_data["book_to_tax_additions"]["line_5"] += float(adjustment.difference)
            elif adjustment.m1_line == "line_6":
                m1_data["book_to_tax_additions"]["line_6"] += float(adjustment.difference)
            elif adjustment.m1_line == "line_8":
                m1_data["tax_to_book_subtractions"]["line_8"] += float(adjustment.difference)
            elif adjustment.m1_line == "line_9":
                m1_data["tax_to_book_subtractions"]["line_9"] += float(adjustment.difference)
            elif adjustment.m1_line == "line_10":
                m1_data["tax_to_book_subtractions"]["line_10"] += float(adjustment.difference)
        
        # Calculate totals
        additions = m1_data["book_to_tax_additions"]
        subtractions = m1_data["tax_to_book_subtractions"]
        
        additions["line_7"] = additions["line_2"] + additions["line_3"] + additions["line_4"] + additions["line_5"] + additions["line_6"]
        subtractions["line_11"] = subtractions["line_8"] + subtractions["line_9"] + subtractions["line_10"]
        subtractions["line_12"] = float(book_income) + additions["line_7"] - subtractions["line_11"]
        
        return m1_data
    
    def generate_adjustment_report(self, adjustments: List[TaxAdjustment]) -> Dict[str, Any]:
        """Generate a detailed report of all adjustments"""
        
        total_additions = sum(adj.difference for adj in adjustments if adj.m1_line in ["line_2", "line_5", "line_6"])
        total_subtractions = sum(adj.difference for adj in adjustments if adj.m1_line in ["line_8", "line_9", "line_10"])
        
        permanent_diffs = [adj for adj in adjustments if adj.permanent]
        timing_diffs = [adj for adj in adjustments if not adj.permanent]
        
        return {
            "summary": {
                "total_adjustments": len(adjustments),
                "total_additions": float(total_additions),
                "total_subtractions": float(total_subtractions),
                "net_adjustment": float(total_additions - total_subtractions),
                "permanent_differences": len(permanent_diffs),
                "timing_differences": len(timing_diffs)
            },
            "adjustments_by_type": {
                "additions": [
                    {
                        "type": adj.adjustment_type,
                        "description": adj.description,
                        "amount": float(adj.difference),
                        "explanation": adj.explanation
                    }
                    for adj in adjustments if adj.m1_line in ["line_2", "line_5", "line_6"]
                ],
                "subtractions": [
                    {
                        "type": adj.adjustment_type,
                        "description": adj.description,
                        "amount": float(adj.difference),
                        "explanation": adj.explanation
                    }
                    for adj in adjustments if adj.m1_line in ["line_8", "line_9", "line_10"]
                ]
            },
            "permanent_vs_timing": {
                "permanent": [
                    {
                        "type": adj.adjustment_type,
                        "description": adj.description,
                        "amount": float(adj.difference)
                    }
                    for adj in permanent_diffs
                ],
                "timing": [
                    {
                        "type": adj.adjustment_type,
                        "description": adj.description,
                        "amount": float(adj.difference)
                    }
                    for adj in timing_diffs
                ]
            }
        }