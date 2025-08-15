import pytest
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import Mock, MagicMock
from decimal import Decimal

from app.services.reconciliation_service import ReconciliationService
from app.models.transactions import TransactionClean
from app.models.reconciliation import LedgerEntry


class TestReconciliationEngine:
    """Test the enhanced reconciliation engine with all four matching algorithms"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        return db
    
    @pytest.fixture
    def reconcile_service(self, mock_db):
        """Create reconciliation service with mocked DB"""
        return ReconciliationService(mock_db)
    
    @pytest.fixture
    def sample_transaction(self):
        """Sample transaction for testing"""
        txn = Mock(spec=TransactionClean)
        txn.id = 1
        txn.amount_base = Decimal('100.00')
        txn.transaction_date = datetime(2024, 1, 15)
        txn.description_normalized = "Coffee Shop Purchase"
        txn.counterparty_normalized = "Local Coffee"
        return txn
    
    @pytest.fixture
    def sample_ledger_entries(self):
        """Sample ledger entries for testing"""
        entries = []
        
        # Exact match candidate
        exact_entry = Mock(spec=LedgerEntry)
        exact_entry.id = 101
        exact_entry.amount_base = Decimal('100.00')
        exact_entry.entry_date = datetime(2024, 1, 15)
        exact_entry.memo = "Coffee expense"
        exact_entry.is_reconciled = "false"
        entries.append(exact_entry)
        
        # Windowed match candidate
        windowed_entry = Mock(spec=LedgerEntry)
        windowed_entry.id = 102
        windowed_entry.amount_base = Decimal('100.00')
        windowed_entry.entry_date = datetime(2024, 1, 18)  # 3 days later
        windowed_entry.memo = "Office supplies"
        windowed_entry.is_reconciled = "false"
        entries.append(windowed_entry)
        
        # Fuzzy match candidate
        fuzzy_entry = Mock(spec=LedgerEntry)
        fuzzy_entry.id = 103
        fuzzy_entry.amount_base = Decimal('95.50')
        fuzzy_entry.entry_date = datetime(2024, 1, 16)
        fuzzy_entry.memo = "Coffee shop downtown purchase"
        fuzzy_entry.is_reconciled = "false"
        entries.append(fuzzy_entry)
        
        # Partial match candidates (sum to 100)
        partial1 = Mock(spec=LedgerEntry)
        partial1.id = 104
        partial1.amount_base = Decimal('60.00')
        partial1.entry_date = datetime(2024, 1, 15)
        partial1.memo = "Partial payment 1"
        partial1.is_reconciled = "false"
        entries.append(partial1)
        
        partial2 = Mock(spec=LedgerEntry)
        partial2.id = 105
        partial2.amount_base = Decimal('40.00')
        partial2.entry_date = datetime(2024, 1, 15)
        partial2.memo = "Partial payment 2"
        partial2.is_reconciled = "false"
        entries.append(partial2)
        
        return entries
    
    def test_exact_matching(self, reconcile_service, sample_transaction, sample_ledger_entries):
        """Test exact matching algorithm"""
        exact_match = reconcile_service._match_exact(
            sample_transaction, 
            sample_ledger_entries[0],  # Exact match candidate
            amount_tolerance=0.01
        )
        
        assert exact_match is not None
        assert exact_match['match_type'] == 'exact'
        assert exact_match['exact_score'] == 1.0
        assert exact_match['ledger_ids'] == [101]
        assert 'Exact match' in exact_match['explain']
    
    def test_windowed_matching(self, reconcile_service, sample_transaction, sample_ledger_entries):
        """Test windowed matching algorithm"""
        windowed_match = reconcile_service._match_windowed(
            sample_transaction,
            sample_ledger_entries[1],  # Windowed match candidate
            amount_tolerance=0.01,
            date_window_days=5
        )
        
        assert windowed_match is not None
        assert windowed_match['match_type'] == 'windowed'
        assert windowed_match['windowed_score'] > 0.5
        assert windowed_match['ledger_ids'] == [102]
        assert 'Windowed match' in windowed_match['explain']
    
    def test_fuzzy_matching(self, reconcile_service, sample_transaction, sample_ledger_entries):
        """Test fuzzy matching algorithm"""
        fuzzy_match = reconcile_service._match_fuzzy(
            sample_transaction,
            sample_ledger_entries[2],  # Fuzzy match candidate
            fuzzy_threshold=0.5  # Lower threshold for testing
        )
        
        assert fuzzy_match is not None
        assert fuzzy_match['match_type'] == 'fuzzy'
        assert fuzzy_match['fuzzy_score'] > 0
        assert fuzzy_match['ledger_ids'] == [103]
        assert 'Fuzzy match' in fuzzy_match['explain']
    
    def test_partial_matching(self, reconcile_service, sample_transaction, sample_ledger_entries):
        """Test partial matching algorithm (subset sum)"""
        # Use only partial match candidates
        partial_candidates = sample_ledger_entries[3:5]  # 60 + 40 = 100
        
        partial_matches = reconcile_service._match_partial(
            sample_transaction,
            partial_candidates,
            amount_tolerance=0.01,
            max_txns=3
        )
        
        assert len(partial_matches) > 0
        best_partial = partial_matches[0]
        assert best_partial['match_type'] == 'partial'
        assert best_partial['partial_score'] > 0
        assert len(best_partial['ledger_ids']) == 2
        assert set(best_partial['ledger_ids']) == {104, 105}
        assert 'Partial match' in best_partial['explain']
    
    def test_unified_scoring(self, reconcile_service):
        """Test unified scoring mechanism"""
        candidate = {
            'exact_score': 1.0,
            'windowed_score': 0.0,
            'fuzzy_score': 0.0,
            'partial_score': 0.0
        }
        
        weights = {'exact': 0.5, 'windowed': 0.2, 'fuzzy': 0.2, 'partial': 0.1}
        score = reconcile_service._calculate_unified_score(candidate, weights)
        
        assert score == 0.5  # Only exact score contributes
        
        # Test mixed scoring
        candidate_mixed = {
            'exact_score': 0.0,
            'windowed_score': 0.8,
            'fuzzy_score': 0.6,
            'partial_score': 0.5
        }
        
        score_mixed = reconcile_service._calculate_unified_score(candidate_mixed, weights)
        expected = 0.2 * 0.8 + 0.2 * 0.6 + 0.1 * 0.5
        assert abs(score_mixed - expected) < 0.001
    
    def test_description_cleaning(self, reconcile_service):
        """Test description cleaning for fuzzy matching"""
        dirty_desc = "Coffee Shop Purchase 2024-01-15 TXN#123456 $100.00"
        clean_desc = reconcile_service._clean_description(dirty_desc)
        
        assert "coffee shop purchase" in clean_desc.lower()
        assert "2024-01-15" not in clean_desc
        assert "123456" not in clean_desc
        assert "$" not in clean_desc
    
    @pytest.mark.asyncio
    async def test_run_reconcile_integration(self, reconcile_service, mock_db):
        """Test the full run_reconcile method integration"""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Mock the helper methods to return empty data
        reconcile_service._get_unreconciled_transactions = Mock(return_value=[])
        reconcile_service._get_unreconciled_ledger_entries = Mock(return_value=[])
        
        result = await reconcile_service.run_reconcile()
        
        assert 'matches' in result
        assert 'auto_match_rate' in result
        assert 'unmatched_txns' in result
        assert 'match_type_counts' in result
        assert isinstance(result['matches'], list)
        assert isinstance(result['auto_match_rate'], (int, float))
    
    def test_weight_validation(self, reconcile_service):
        """Test that weights work correctly"""
        # Test default weights
        default_weights = {'exact': 0.5, 'windowed': 0.2, 'fuzzy': 0.2, 'partial': 0.1}
        assert sum(default_weights.values()) == 1.0
        
        # Test custom weights
        custom_weights = {'exact': 0.6, 'windowed': 0.3, 'fuzzy': 0.1, 'partial': 0.0}
        candidate = {
            'exact_score': 1.0,
            'windowed_score': 0.5,
            'fuzzy_score': 0.8,
            'partial_score': 0.3
        }
        
        score = reconcile_service._calculate_unified_score(candidate, custom_weights)
        expected = 0.6 * 1.0 + 0.3 * 0.5 + 0.1 * 0.8 + 0.0 * 0.3
        assert abs(score - expected) < 0.001
    
    def test_matching_thresholds(self, reconcile_service, sample_transaction):
        """Test various matching thresholds"""
        # Test amount tolerance
        ledger_close = Mock(spec=LedgerEntry)
        ledger_close.id = 200
        ledger_close.amount_base = Decimal('100.05')  # 5 cents difference
        ledger_close.entry_date = datetime(2024, 1, 15)
        ledger_close.memo = "Test"
        ledger_close.is_reconciled = "false"
        
        # Should match with 0.1 tolerance
        match_loose = reconcile_service._match_exact(sample_transaction, ledger_close, 0.1)
        assert match_loose is not None
        
        # Should not match with 0.01 tolerance
        match_strict = reconcile_service._match_exact(sample_transaction, ledger_close, 0.01)
        assert match_strict is None
    
    def test_edge_cases(self, reconcile_service, sample_transaction):
        """Test edge cases and error conditions"""
        # Test with None/empty descriptions for fuzzy matching
        empty_ledger = Mock(spec=LedgerEntry)
        empty_ledger.id = 300
        empty_ledger.amount_base = Decimal('100.00')
        empty_ledger.entry_date = datetime(2024, 1, 15)
        empty_ledger.memo = None
        empty_ledger.is_reconciled = "false"
        
        fuzzy_result = reconcile_service._match_fuzzy(sample_transaction, empty_ledger, 0.85)
        assert fuzzy_result is None
        
        # Test partial matching with empty ledger list
        partial_results = reconcile_service._match_partial(sample_transaction, [], 0.01, 3)
        assert len(partial_results) == 0
        
        # Test with zero amounts
        zero_txn = Mock(spec=TransactionClean)
        zero_txn.amount_base = Decimal('0.00')
        zero_txn.transaction_date = datetime(2024, 1, 15)
        
        zero_ledger = Mock(spec=LedgerEntry)
        zero_ledger.amount_base = Decimal('0.00')
        zero_ledger.entry_date = datetime(2024, 1, 15)
        
        exact_zero = reconcile_service._match_exact(zero_txn, zero_ledger, 0.01)
        assert exact_zero is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])