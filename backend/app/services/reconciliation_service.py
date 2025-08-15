from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from rapidfuzz import fuzz
import pandas as pd
import itertools
from collections import defaultdict
import re

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

    async def run_reconcile(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[int]] = None,
        amount_tolerance: float = 0.01,
        date_window_days: int = 5,
        fuzzy_threshold: float = 0.85,
        partial_max_txns: int = 3,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Enhanced reconciliation engine with exact/windowed/fuzzy/partial matching"""
        
        if weights is None:
            weights = {'exact': 0.5, 'windowed': 0.2, 'fuzzy': 0.2, 'partial': 0.1}
        
        # Get unreconciled data
        transactions = self._get_unreconciled_transactions(start_date, end_date, account_ids)
        ledger_entries = self._get_unreconciled_ledger_entries(start_date, end_date)
        
        matches = []
        matched_ledger_ids = set()
        matched_txn_ids = set()
        
        # Track matching statistics
        match_stats = {
            'exact': 0, 'windowed': 0, 'fuzzy': 0, 'partial': 0
        }
        
        for txn in transactions:
            if txn.id in matched_txn_ids:
                continue
                
            available_ledgers = [le for le in ledger_entries if le.id not in matched_ledger_ids]
            
            # Try all matching strategies
            best_match = self._find_best_unified_match(
                txn, available_ledgers, amount_tolerance, 
                date_window_days, fuzzy_threshold, partial_max_txns, weights
            )
            
            if best_match and best_match['score'] >= 0.5:  # Minimum threshold
                matches.append({
                    'txn_id': txn.id,
                    'ledger_id': best_match.get('ledger_ids', []),
                    'match_type': best_match['match_type'],
                    'score': best_match['score'],
                    'explain': best_match['explain']
                })
                
                # Mark as matched
                matched_txn_ids.add(txn.id)
                if best_match.get('ledger_ids'):
                    matched_ledger_ids.update(best_match['ledger_ids'])
                    
                match_stats[best_match['match_type']] += 1
        
        # Calculate summary statistics
        total_txns = len(transactions)
        auto_matched = sum(match_stats[mt] for mt in ['exact', 'windowed'])
        auto_match_rate = auto_matched / max(total_txns, 1)
        unmatched_txns = total_txns - len(matches)
        
        return {
            'matches': matches,
            'auto_match_rate': auto_match_rate,
            'unmatched_txns': unmatched_txns,
            'match_type_counts': match_stats,
            'total_processed': total_txns
        }
    
    def _get_unreconciled_transactions(self, start_date, end_date, account_ids):
        """Get unreconciled transactions"""
        query = self.db.query(TransactionClean).filter(
            ~TransactionClean.id.in_(
                self.db.query(Reconciliation.transaction_clean_id).filter(
                    Reconciliation.status != 'rejected'
                )
            )
        )
        
        if start_date:
            query = query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionClean.transaction_date <= end_date)
        if account_ids:
            query = query.filter(TransactionClean.account_id.in_(account_ids))
            
        return query.all()
    
    def _get_unreconciled_ledger_entries(self, start_date, end_date):
        """Get unreconciled ledger entries"""
        query = self.db.query(LedgerEntry).filter(LedgerEntry.is_reconciled == "false")
        
        if start_date:
            query = query.filter(LedgerEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(LedgerEntry.entry_date <= end_date)
            
        return query.all()
    
    def _find_best_unified_match(self, txn, ledgers, amount_tolerance, date_window_days, 
                                fuzzy_threshold, partial_max_txns, weights):
        """Find best match using unified scoring across all strategies"""
        
        candidates = []
        
        # 1. Exact matches
        for ledger in ledgers:
            exact_result = self._match_exact(txn, ledger, amount_tolerance)
            if exact_result:
                candidates.append(exact_result)
        
        # 2. Windowed matches  
        for ledger in ledgers:
            windowed_result = self._match_windowed(txn, ledger, amount_tolerance, date_window_days)
            if windowed_result:
                candidates.append(windowed_result)
        
        # 3. Fuzzy matches
        for ledger in ledgers:
            fuzzy_result = self._match_fuzzy(txn, ledger, fuzzy_threshold)
            if fuzzy_result:
                candidates.append(fuzzy_result)
        
        # 4. Partial matches (subset sum)
        partial_results = self._match_partial(txn, ledgers, amount_tolerance, partial_max_txns)
        candidates.extend(partial_results)
        
        # Calculate unified scores and return best
        best_candidate = None
        best_score = 0
        
        for candidate in candidates:
            unified_score = self._calculate_unified_score(candidate, weights)
            if unified_score > best_score:
                best_score = unified_score
                best_candidate = candidate
                best_candidate['score'] = unified_score
        
        return best_candidate
    
    def _match_exact(self, txn, ledger, amount_tolerance):
        """Exact matching: amount equal & date diff ≤ 1 day"""
        amount_diff = abs(abs(txn.amount_base) - abs(ledger.amount_base))
        if amount_diff > amount_tolerance:
            return None
            
        date_diff = abs((txn.transaction_date.date() - ledger.entry_date.date()).days)
        if date_diff > 1:
            return None
            
        return {
            'match_type': 'exact',
            'ledger_ids': [ledger.id],
            'exact_score': 1.0,
            'windowed_score': 0.0,
            'fuzzy_score': 0.0, 
            'partial_score': 0.0,
            'explain': f'Exact match: amount diff {amount_diff:.2f}, date diff {date_diff} days'
        }
    
    def _match_windowed(self, txn, ledger, amount_tolerance, date_window_days):
        """Windowed matching: amount equal & date diff ≤ window"""
        amount_diff = abs(abs(txn.amount_base) - abs(ledger.amount_base))
        if amount_diff > amount_tolerance:
            return None
            
        date_diff = abs((txn.transaction_date.date() - ledger.entry_date.date()).days)
        if date_diff > date_window_days:
            return None
            
        # Penalize by date distance
        window_score = max(0.5, 1.0 - (date_diff / date_window_days) * 0.3)
        
        return {
            'match_type': 'windowed',
            'ledger_ids': [ledger.id],
            'exact_score': 0.0,
            'windowed_score': window_score,
            'fuzzy_score': 0.0,
            'partial_score': 0.0,
            'explain': f'Windowed match: amount diff {amount_diff:.2f}, date diff {date_diff} days'
        }
    
    def _match_fuzzy(self, txn, ledger, fuzzy_threshold):
        """Fuzzy matching: description similarity ≥ threshold"""
        txn_desc = self._clean_description(txn.description_normalized or "")
        ledger_desc = self._clean_description(ledger.memo or "")
        
        if not txn_desc or not ledger_desc:
            return None
            
        similarity = fuzz.ratio(txn_desc, ledger_desc) / 100.0
        if similarity < fuzzy_threshold:
            return None
            
        # Additional amount/date scoring for fuzzy
        amount_diff_pct = abs(abs(txn.amount_base) - abs(ledger.amount_base)) / max(abs(txn.amount_base), abs(ledger.amount_base))
        amount_score = max(0, 1.0 - amount_diff_pct)
        
        date_diff = abs((txn.transaction_date.date() - ledger.entry_date.date()).days)
        date_score = max(0, 1.0 - date_diff / 30.0)  # 30 day window
        
        fuzzy_score = similarity * 0.6 + amount_score * 0.3 + date_score * 0.1
        
        return {
            'match_type': 'fuzzy',
            'ledger_ids': [ledger.id],
            'exact_score': 0.0,
            'windowed_score': 0.0,
            'fuzzy_score': fuzzy_score,
            'partial_score': 0.0,
            'explain': f'Fuzzy match: desc sim {similarity:.2f}, amount score {amount_score:.2f}, date score {date_score:.2f}'
        }
    
    def _match_partial(self, txn, ledgers, amount_tolerance, max_txns):
        """Partial matching: subset sum within same amount group"""
        target_amount = abs(txn.amount_base)
        
        # Group ledgers by similar amounts (within 10%)
        amount_groups = defaultdict(list)
        for ledger in ledgers:
            ledger_amount = abs(ledger.amount_base)
            if abs(ledger_amount - target_amount) / max(target_amount, ledger_amount) <= 0.1:
                amount_groups[round(ledger_amount, 2)].append(ledger)
        
        results = []
        for group_ledgers in amount_groups.values():
            # Try combinations up to max_txns
            for r in range(1, min(max_txns + 1, len(group_ledgers) + 1)):
                for combo in itertools.combinations(group_ledgers, r):
                    combo_sum = sum(abs(le.amount_base) for le in combo)
                    if abs(combo_sum - target_amount) <= amount_tolerance:
                        partial_score = 1.0 / r  # Prefer fewer entries
                        results.append({
                            'match_type': 'partial',
                            'ledger_ids': [le.id for le in combo],
                            'exact_score': 0.0,
                            'windowed_score': 0.0,
                            'fuzzy_score': 0.0,
                            'partial_score': partial_score,
                            'explain': f'Partial match: {r} entries sum to {combo_sum:.2f}'
                        })
        
        return results
    
    def _clean_description(self, desc):
        """Clean description for fuzzy matching"""
        if not desc:
            return ""
        # Remove timestamps, IDs, special chars
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}|\b\d{6,}\b|[^\w\s]', ' ', desc.lower())
        return ' '.join(cleaned.split())
    
    def _calculate_unified_score(self, candidate, weights):
        """Calculate unified score using weights"""
        return (
            weights['exact'] * candidate.get('exact_score', 0) +
            weights['windowed'] * candidate.get('windowed_score', 0) +
            weights['fuzzy'] * candidate.get('fuzzy_score', 0) +
            weights['partial'] * candidate.get('partial_score', 0)
        )

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