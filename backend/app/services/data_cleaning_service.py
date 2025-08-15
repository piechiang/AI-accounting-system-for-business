from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import re
from datetime import datetime, date

from app.models.transactions import TransactionRaw, TransactionClean

class DataCleaningService:
    def __init__(self):
        self.currency_symbols = {
            '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY',
            '₹': 'INR', 'C$': 'CAD', 'A$': 'AUD'
        }
        
        # Common description cleaning patterns
        self.cleaning_patterns = [
            (r'\s+', ' '),  # Multiple spaces to single space
            (r'^(DEBIT|CREDIT|ACH|WIRE|CHECK|CARD)\s*', ''),  # Remove transaction type prefixes
            (r'\s*\d{2}/\d{2}(/\d{4})?\s*', ' '),  # Remove dates from descriptions
            (r'\s*#\d+\s*', ' '),  # Remove reference numbers
            (r'\s*\*+\d+\s*', ' '),  # Remove masked card numbers
            (r'\s+(LLC|INC|CORP|LTD)\.?\s*$', ''),  # Standardize company suffixes
        ]

    async def clean_transactions(self, raw_transactions: List[TransactionRaw]) -> int:
        """Clean and normalize raw transactions"""
        cleaned_count = 0
        
        for raw_txn in raw_transactions:
            # Skip if already cleaned
            existing_clean = self.db.query(TransactionClean).filter(
                TransactionClean.raw_id == raw_txn.id
            ).first()
            if existing_clean:
                continue
            
            # Clean and normalize data
            cleaned_data = self._clean_transaction_data(raw_txn)
            
            # Create clean transaction record
            clean_txn = TransactionClean(
                raw_id=raw_txn.id,
                transaction_date=cleaned_data['transaction_date'],
                amount_base=cleaned_data['amount_base'],
                currency_base=cleaned_data['currency_base'],
                description_normalized=cleaned_data['description_normalized'],
                counterparty_normalized=cleaned_data['counterparty_normalized'],
                processed_at=datetime.utcnow()
            )
            
            self.db.add(clean_txn)
            cleaned_count += 1
        
        self.db.commit()
        return cleaned_count

    def _clean_transaction_data(self, raw_txn: TransactionRaw) -> Dict[str, Any]:
        """Clean individual transaction data"""
        return {
            'transaction_date': self._normalize_date(raw_txn.transaction_date),
            'amount_base': self._normalize_amount(raw_txn.amount, raw_txn.currency),
            'currency_base': self._get_base_currency(raw_txn.currency),
            'description_normalized': self._normalize_description(raw_txn.description),
            'counterparty_normalized': self._normalize_counterparty(raw_txn.counterparty)
        }

    def _normalize_date(self, date_value: datetime) -> datetime:
        """Normalize date to standard format"""
        if isinstance(date_value, str):
            # Try multiple date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {date_value}")
        return date_value

    def _normalize_amount(self, amount: float, currency: str) -> float:
        """Normalize amount to base currency"""
        # For now, assume USD as base currency
        # In production, you'd implement currency conversion
        if currency == 'USD':
            return amount
        
        # Placeholder for currency conversion
        conversion_rates = {
            'EUR': 1.1, 'GBP': 1.25, 'CAD': 0.8, 'AUD': 0.7
        }
        
        rate = conversion_rates.get(currency, 1.0)
        return amount * rate

    def _get_base_currency(self, currency: str) -> str:
        """Get base currency"""
        return 'USD'  # For now, always use USD as base

    def _normalize_description(self, description: str) -> str:
        """Clean and normalize transaction description"""
        if not description:
            return ""
        
        desc = description.upper().strip()
        
        # Apply cleaning patterns
        for pattern, replacement in self.cleaning_patterns:
            desc = re.sub(pattern, replacement, desc)
        
        # Remove extra whitespace
        desc = ' '.join(desc.split())
        
        return desc

    def _normalize_counterparty(self, counterparty: Optional[str]) -> Optional[str]:
        """Clean and normalize counterparty name"""
        if not counterparty:
            return None
        
        party = counterparty.upper().strip()
        
        # Common normalizations
        normalizations = {
            r'WALMART.*': 'WALMART',
            r'AMAZON.*': 'AMAZON', 
            r'STARBUCKS.*': 'STARBUCKS',
            r'SHELL.*': 'SHELL',
            r'EXXON.*': 'EXXON MOBIL',
            r'TARGET.*': 'TARGET',
            r'HOME DEPOT.*': 'HOME DEPOT',
            r'LOWES.*': 'LOWES'
        }
        
        for pattern, replacement in normalizations.items():
            if re.match(pattern, party):
                return replacement
        
        # Remove common suffixes/prefixes
        party = re.sub(r'\s*(LLC|INC|CORP|LTD|CO)\.?\s*$', '', party)
        party = re.sub(r'^(THE\s+)', '', party)
        
        return party.strip()

    def detect_duplicates(self, transactions: List[TransactionRaw]) -> List[Dict[str, Any]]:
        """Detect potential duplicate transactions"""
        duplicates = []
        
        # Create DataFrame for easier analysis
        df = pd.DataFrame([{
            'id': t.id,
            'date': t.transaction_date,
            'amount': t.amount,
            'description': t.description,
            'counterparty': t.counterparty
        } for t in transactions])
        
        # Group by similar transactions
        duplicate_groups = df.groupby([
            'date', 'amount', 
            df['description'].str[:20]  # First 20 characters
        ]).filter(lambda x: len(x) > 1)
        
        for group_key, group in duplicate_groups.groupby(['date', 'amount']):
            if len(group) > 1:
                duplicates.append({
                    'transaction_ids': group['id'].tolist(),
                    'date': group_key[0],
                    'amount': group_key[1],
                    'count': len(group),
                    'confidence': 0.9  # High confidence for exact amount/date matches
                })
        
        return duplicates

    def get_data_quality_report(self, transactions: List[TransactionRaw]) -> Dict[str, Any]:
        """Generate data quality report"""
        if not transactions:
            return {'error': 'No transactions provided'}
        
        total_count = len(transactions)
        
        # Check for missing data
        missing_descriptions = sum(1 for t in transactions if not t.description)
        missing_counterparties = sum(1 for t in transactions if not t.counterparty)
        missing_amounts = sum(1 for t in transactions if not t.amount or t.amount == 0)
        
        # Check for outliers
        amounts = [t.amount for t in transactions if t.amount]
        if amounts:
            q75, q25 = np.percentile(amounts, [75, 25])
            iqr = q75 - q25
            outlier_threshold = q75 + 1.5 * iqr
            outliers = sum(1 for amount in amounts if amount > outlier_threshold)
        else:
            outliers = 0
        
        # Date range analysis
        dates = [t.transaction_date for t in transactions]
        date_range = {
            'earliest': min(dates),
            'latest': max(dates),
            'span_days': (max(dates) - min(dates)).days
        }
        
        return {
            'total_transactions': total_count,
            'completeness': {
                'missing_descriptions': missing_descriptions,
                'missing_counterparties': missing_counterparties,
                'missing_amounts': missing_amounts,
                'completeness_score': 1 - (missing_descriptions + missing_counterparties + missing_amounts) / (total_count * 3)
            },
            'data_quality': {
                'potential_outliers': outliers,
                'outlier_percentage': outliers / total_count if total_count > 0 else 0
            },
            'date_range': date_range,
            'recommendations': self._generate_recommendations(missing_descriptions, missing_counterparties, outliers, total_count)
        }

    def _generate_recommendations(self, missing_desc: int, missing_parties: int, outliers: int, total: int) -> List[str]:
        """Generate data quality recommendations"""
        recommendations = []
        
        if missing_desc / total > 0.1:
            recommendations.append("Consider improving description capture - over 10% missing")
        
        if missing_parties / total > 0.2:
            recommendations.append("Consider adding counterparty information for better categorization")
        
        if outliers / total > 0.05:
            recommendations.append("Review high-value transactions for accuracy")
        
        if not recommendations:
            recommendations.append("Data quality looks good!")
        
        return recommendations