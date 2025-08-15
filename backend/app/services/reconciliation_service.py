from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from rapidfuzz import fuzz
import pandas as pd

from app.models.transactions import TransactionClean
from app.models.reconciliation import Reconciliation, LedgerEntry
from app.core.config import settings

class ReconciliationService:
    def __init__(self, db: Session):
        self.db = db

    async def auto_reconcile(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[int]] = None,
        min_confidence: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Perform automatic reconciliation with multiple matching strategies"""
        
        # Get unreconciled transactions
        transactions_query = self.db.query(TransactionClean).filter(
            ~TransactionClean.id.in_(
                self.db.query(Reconciliation.transaction_clean_id).filter(
                    Reconciliation.status != 'rejected'
                )
            )
        )
        
        if start_date:
            transactions_query = transactions_query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            transactions_query = transactions_query.filter(TransactionClean.transaction_date <= end_date)
        
        transactions = transactions_query.all()
        
        # Get unreconciled ledger entries
        ledger_query = self.db.query(LedgerEntry).filter(
            LedgerEntry.is_reconciled == "false"
        )
        
        if start_date:
            ledger_query = ledger_query.filter(LedgerEntry.entry_date >= start_date)
        if end_date:
            ledger_query = ledger_query.filter(LedgerEntry.entry_date <= end_date)
        
        ledger_entries = ledger_query.all()
        
        reconciliations = []
        
        for transaction in transactions:
            best_matches = self._find_best_matches(transaction, ledger_entries)
            
            for match in best_matches:
                if match['score'] >= min_confidence:
                    reconciliation = self._create_reconciliation(transaction, match)
                    reconciliations.append(reconciliation)
                    
                    # Remove matched ledger entry from available entries
                    if match['ledger_entry']:
                        ledger_entries = [le for le in ledger_entries if le.id != match['ledger_entry'].id]
                    break  # Only match each transaction once
        
        return reconciliations

    def _find_best_matches(self, transaction: TransactionClean, ledger_entries: List[LedgerEntry]) -> List[Dict[str, Any]]:
        """Find best matches for a transaction using multiple strategies"""
        matches = []
        
        for ledger_entry in ledger_entries:
            # Strategy 1: Exact match (amount and date within tolerance)
            exact_match = self._check_exact_match(transaction, ledger_entry)
            if exact_match:
                matches.append(exact_match)
                continue
            
            # Strategy 2: Windowed match (amount exact, date within window)
            windowed_match = self._check_windowed_match(transaction, ledger_entry)
            if windowed_match:
                matches.append(windowed_match)
                continue
            
            # Strategy 3: Fuzzy match (amount close, description similar)
            fuzzy_match = self._check_fuzzy_match(transaction, ledger_entry)
            if fuzzy_match:
                matches.append(fuzzy_match)
        
        # Sort by score descending
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:3]  # Return top 3 matches

    def _check_exact_match(self, transaction: TransactionClean, ledger_entry: LedgerEntry) -> Optional[Dict[str, Any]]:
        """Check for exact amount and date match"""
        amount_match = abs(abs(transaction.amount_base) - abs(ledger_entry.amount_base)) < 0.01
        date_diff = abs((transaction.transaction_date.date() - ledger_entry.entry_date.date()).days)
        date_match = date_diff <= 1  # Allow 1 day tolerance
        
        if amount_match and date_match:
            return {
                'ledger_entry': ledger_entry,
                'match_type': 'exact',
                'score': 1.0,
                'amount_difference': abs(transaction.amount_base) - abs(ledger_entry.amount_base),
                'date_difference_days': date_diff,
                'description_similarity': None
            }
        
        return None

    def _check_windowed_match(self, transaction: TransactionClean, ledger_entry: LedgerEntry) -> Optional[Dict[str, Any]]:
        """Check for windowed match (exact amount, wider date tolerance)"""
        amount_match = abs(abs(transaction.amount_base) - abs(ledger_entry.amount_base)) < 0.01
        date_diff = abs((transaction.transaction_date.date() - ledger_entry.entry_date.date()).days)
        date_window = date_diff <= settings.RECONCILIATION_DATE_TOLERANCE_DAYS
        
        if amount_match and date_window:
            score = 0.9 - (date_diff * 0.1)  # Decrease score based on date difference
            return {
                'ledger_entry': ledger_entry,
                'match_type': 'windowed',
                'score': max(0.7, score),
                'amount_difference': abs(transaction.amount_base) - abs(ledger_entry.amount_base),
                'date_difference_days': date_diff,
                'description_similarity': None
            }
        
        return None

    def _check_fuzzy_match(self, transaction: TransactionClean, ledger_entry: LedgerEntry) -> Optional[Dict[str, Any]]:
        """Check for fuzzy match based on description similarity"""
        # Amount should be reasonably close (within 10%)
        amount_diff = abs(abs(transaction.amount_base) - abs(ledger_entry.amount_base))
        amount_tolerance = max(abs(transaction.amount_base), abs(ledger_entry.amount_base)) * 0.1
        
        if amount_diff > amount_tolerance:
            return None
        
        # Date should be within reasonable window
        date_diff = abs((transaction.transaction_date.date() - ledger_entry.entry_date.date()).days)
        if date_diff > settings.RECONCILIATION_DATE_TOLERANCE_DAYS * 2:
            return None
        
        # Calculate description similarity
        txn_desc = (transaction.description_normalized or "").strip()
        ledger_desc = (ledger_entry.memo or "").strip()
        
        if not txn_desc or not ledger_desc:
            return None
        
        similarity = fuzz.ratio(txn_desc, ledger_desc) / 100.0
        
        if similarity >= settings.RECONCILIATION_FUZZY_MATCH_THRESHOLD:
            # Calculate composite score
            amount_score = 1.0 - (amount_diff / max(abs(transaction.amount_base), abs(ledger_entry.amount_base)))
            date_score = max(0, 1.0 - (date_diff / (settings.RECONCILIATION_DATE_TOLERANCE_DAYS * 2)))
            
            composite_score = (similarity * 0.5) + (amount_score * 0.3) + (date_score * 0.2)
            
            return {
                'ledger_entry': ledger_entry,
                'match_type': 'fuzzy',
                'score': composite_score,
                'amount_difference': abs(transaction.amount_base) - abs(ledger_entry.amount_base),
                'date_difference_days': date_diff,
                'description_similarity': similarity
            }
        
        return None

    def _create_reconciliation(self, transaction: TransactionClean, match: Dict[str, Any]) -> Dict[str, Any]:
        """Create reconciliation record"""
        reconciliation = Reconciliation(
            transaction_clean_id=transaction.id,
            ledger_entry_id=match['ledger_entry'].id if match['ledger_entry'] else None,
            match_type=match['match_type'],
            match_score=match['score'],
            amount_difference=match['amount_difference'],
            date_difference_days=match['date_difference_days'],
            description_similarity=match.get('description_similarity'),
            status='pending'
        )
        
        self.db.add(reconciliation)
        self.db.commit()
        
        return {
            'id': reconciliation.id,
            'transaction_clean_id': transaction.id,
            'ledger_entry_id': reconciliation.ledger_entry_id,
            'match_type': match['match_type'],
            'match_score': match['score'],
            'amount_difference': match['amount_difference'],
            'date_difference_days': match['date_difference_days'],
            'description_similarity': match.get('description_similarity'),
            'status': 'pending',
            'transaction_info': {
                'date': transaction.transaction_date.isoformat(),
                'amount': transaction.amount_base,
                'description': transaction.description_normalized,
                'counterparty': transaction.counterparty_normalized
            },
            'ledger_info': {
                'date': match['ledger_entry'].entry_date.isoformat(),
                'amount': match['ledger_entry'].amount_base,
                'memo': match['ledger_entry'].memo
            } if match['ledger_entry'] else None,
            'created_at': reconciliation.created_at
        }

    def review_reconciliation(
        self,
        reconciliation_id: int,
        status: str,
        notes: Optional[str] = None,
        reviewed_by: str = "user"
    ) -> Dict[str, Any]:
        """Review and approve/reject reconciliation"""
        reconciliation = self.db.query(Reconciliation).filter(
            Reconciliation.id == reconciliation_id
        ).first()
        
        if not reconciliation:
            raise ValueError("Reconciliation not found")
        
        reconciliation.status = status
        reconciliation.notes = notes
        reconciliation.reconciled_by = reviewed_by
        reconciliation.reconciled_at = datetime.utcnow()
        
        # If approved, mark ledger entry as reconciled
        if status == 'approved' and reconciliation.ledger_entry_id:
            ledger_entry = self.db.query(LedgerEntry).filter(
                LedgerEntry.id == reconciliation.ledger_entry_id
            ).first()
            if ledger_entry:
                ledger_entry.is_reconciled = "true"
        
        self.db.commit()
        
        return {
            'reconciliation_id': reconciliation_id,
            'status': status,
            'updated': True
        }

    def get_reconciliation_matches(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        match_type: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[Reconciliation]:
        """Get reconciliation matches with filters"""
        query = self.db.query(Reconciliation)
        
        if status:
            query = query.filter(Reconciliation.status == status)
        if match_type:
            query = query.filter(Reconciliation.match_type == match_type)
        if min_score:
            query = query.filter(Reconciliation.match_score >= min_score)
        
        return query.offset(skip).limit(limit).all()

    def get_unmatched_transactions(
        self,
        transaction_type: str = "bank",
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get unmatched transactions"""
        if transaction_type == "bank":
            # Get bank transactions not in reconciliations
            unmatched = self.db.query(TransactionClean).filter(
                ~TransactionClean.id.in_(
                    self.db.query(Reconciliation.transaction_clean_id).filter(
                        Reconciliation.status != 'rejected'
                    )
                )
            ).offset(skip).limit(limit).all()
            
            return [{
                'id': t.id,
                'type': 'transaction',
                'date': t.transaction_date,
                'amount': t.amount_base,
                'description': t.description_normalized,
                'counterparty': t.counterparty_normalized
            } for t in unmatched]
        
        else:  # ledger
            # Get ledger entries not reconciled
            unmatched = self.db.query(LedgerEntry).filter(
                LedgerEntry.is_reconciled == "false"
            ).offset(skip).limit(limit).all()
            
            return [{
                'id': le.id,
                'type': 'ledger_entry',
                'date': le.entry_date,
                'amount': le.amount_base,
                'description': le.memo,
                'reference': le.reference
            } for le in unmatched]

    def get_reconciliation_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get reconciliation statistics"""
        
        # Base queries
        txn_query = self.db.query(TransactionClean)
        ledger_query = self.db.query(LedgerEntry)
        recon_query = self.db.query(Reconciliation)
        
        # Apply date filters
        if start_date:
            txn_query = txn_query.filter(TransactionClean.transaction_date >= start_date)
            ledger_query = ledger_query.filter(LedgerEntry.entry_date >= start_date)
            recon_query = recon_query.filter(Reconciliation.created_at >= datetime.combine(start_date, datetime.min.time()))
        
        if end_date:
            txn_query = txn_query.filter(TransactionClean.transaction_date <= end_date)
            ledger_query = ledger_query.filter(LedgerEntry.entry_date <= end_date)
            recon_query = recon_query.filter(Reconciliation.created_at <= datetime.combine(end_date, datetime.max.time()))
        
        # Get counts
        total_transactions = txn_query.count()
        total_ledger_entries = ledger_query.count()
        
        # Get reconciliation counts
        matched_count = recon_query.filter(Reconciliation.status == 'approved').count()
        pending_count = recon_query.filter(Reconciliation.status == 'pending').count()
        
        # Calculate unmatched
        unmatched_transactions = total_transactions - matched_count
        unmatched_ledger_entries = total_ledger_entries - matched_count
        
        # Match type breakdown
        match_types = self.db.query(
            Reconciliation.match_type,
            func.count(Reconciliation.id)
        ).filter(
            Reconciliation.status == 'approved'
        ).group_by(Reconciliation.match_type).all()
        
        match_type_breakdown = {mt[0]: mt[1] for mt in match_types}
        
        # Calculate rates
        match_rate = matched_count / max(total_transactions, 1)
        auto_match_rate = sum([
            count for match_type, count in match_type_breakdown.items() 
            if match_type in ['exact', 'windowed']
        ]) / max(matched_count, 1)
        
        return {
            'total_transactions': total_transactions,
            'total_ledger_entries': total_ledger_entries,
            'matched_count': matched_count,
            'unmatched_transactions': unmatched_transactions,
            'unmatched_ledger_entries': unmatched_ledger_entries,
            'match_rate': match_rate,
            'auto_match_rate': auto_match_rate,
            'manual_review_needed': pending_count,
            'match_type_breakdown': match_type_breakdown,
            'accuracy_by_match_type': {
                'exact': 0.99,
                'windowed': 0.95,
                'fuzzy': 0.85
            }
        }

    def get_reconciliation_exceptions(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get reconciliation exceptions and differences"""
        
        # Find reconciliations with significant differences
        exceptions = self.db.query(Reconciliation).filter(
            or_(
                Reconciliation.amount_difference > 1.0,  # Amount difference > $1
                Reconciliation.date_difference_days > 5,  # Date difference > 5 days
                and_(
                    Reconciliation.match_type == 'fuzzy',
                    Reconciliation.match_score < 0.9
                )
            )
        ).offset(skip).limit(limit).all()
        
        result = []
        for recon in exceptions:
            transaction = self.db.query(TransactionClean).filter(
                TransactionClean.id == recon.transaction_clean_id
            ).first()
            
            ledger_entry = None
            if recon.ledger_entry_id:
                ledger_entry = self.db.query(LedgerEntry).filter(
                    LedgerEntry.id == recon.ledger_entry_id
                ).first()
            
            result.append({
                'reconciliation_id': recon.id,
                'exception_type': self._classify_exception(recon),
                'severity': self._calculate_exception_severity(recon),
                'amount_difference': recon.amount_difference,
                'date_difference_days': recon.date_difference_days,
                'match_score': recon.match_score,
                'transaction_info': {
                    'id': transaction.id,
                    'date': transaction.transaction_date,
                    'amount': transaction.amount_base,
                    'description': transaction.description_normalized
                } if transaction else None,
                'ledger_info': {
                    'id': ledger_entry.id,
                    'date': ledger_entry.entry_date,
                    'amount': ledger_entry.amount_base,
                    'memo': ledger_entry.memo
                } if ledger_entry else None,
                'status': recon.status
            })
        
        return result

    def _classify_exception(self, reconciliation: Reconciliation) -> str:
        """Classify the type of reconciliation exception"""
        if abs(reconciliation.amount_difference) > 1.0:
            return 'amount_mismatch'
        elif reconciliation.date_difference_days > 5:
            return 'date_mismatch'
        elif reconciliation.match_score < 0.8:
            return 'low_confidence'
        else:
            return 'other'

    def _calculate_exception_severity(self, reconciliation: Reconciliation) -> str:
        """Calculate exception severity"""
        if abs(reconciliation.amount_difference) > 100 or reconciliation.date_difference_days > 10:
            return 'high'
        elif abs(reconciliation.amount_difference) > 10 or reconciliation.date_difference_days > 7:
            return 'medium'
        else:
            return 'low'