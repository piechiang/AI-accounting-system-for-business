#!/usr/bin/env python3
"""
Evaluate reconciliation engine performance.
Loads synthetic data, runs reconciliation, and calculates match rates.
"""

import json
import csv
import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any
import sys
import os


class ReconciliationEvaluator:
    """Evaluate reconciliation engine performance against known ground truth"""
    
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url.rstrip('/')
        self.ground_truth = {}
        self.results = {}
    
    def load_ground_truth(self, txn_file="synthetic_transactions.csv", 
                         ledger_file="synthetic_ledger_entries.csv"):
        """Load synthetic data with known match types"""
        print(f"Loading ground truth from {txn_file} and {ledger_file}")
        
        # Load transactions
        transactions = {}
        with open(txn_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn_id = int(row['id'])
                transactions[txn_id] = {
                    'id': txn_id,
                    'amount': Decimal(row['amount_base']),
                    'date': row['transaction_date'],
                    'description': row['description_normalized'],
                    'expected_match_type': row['expected_match_type']
                }
        
        # Load ledger entries  
        ledger_entries = {}
        with open(ledger_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ledger_id = int(row['id'])
                ledger_entries[ledger_id] = {
                    'id': ledger_id,
                    'amount': Decimal(row['amount_base']),
                    'date': row['entry_date'],
                    'memo': row['memo']
                }
        
        self.ground_truth = {
            'transactions': transactions,
            'ledger_entries': ledger_entries
        }
        
        print(f"Loaded {len(transactions)} transactions and {len(ledger_entries)} ledger entries")
        return True
    
    def call_reconciliation_api(self, config=None):
        """Call the /reconcile/run endpoint"""
        if config is None:
            config = {
                "amount_tolerance": 0.01,
                "date_window_days": 5,
                "fuzzy_threshold": 0.85,
                "partial_max_txns": 3,
                "weights": {
                    "exact": 0.5,
                    "windowed": 0.2,
                    "fuzzy": 0.2,
                    "partial": 0.1
                }
            }
        
        url = f"{self.api_base_url}/reconcile/run"
        
        print(f"Calling reconciliation API: {url}")
        print(f"Configuration: {json.dumps(config, indent=2)}")
        
        try:
            response = requests.post(url, json=config, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            self.results = result
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            return None
    
    def evaluate_performance(self):
        """Evaluate reconciliation performance against ground truth"""
        if not self.results or not self.ground_truth:
            print("Error: Missing results or ground truth data")
            return None
        
        print("\n" + "="*60)
        print("RECONCILIATION PERFORMANCE EVALUATION")
        print("="*60)
        
        matches = self.results.get('matches', [])
        total_txns = len(self.ground_truth['transactions'])
        
        # Overall statistics
        print(f"\nOverall Statistics:")
        print(f"- Total transactions: {total_txns}")
        print(f"- Matches found: {len(matches)}")
        print(f"- Overall match rate: {len(matches)/total_txns:.1%}")
        print(f"- Auto-match rate (from API): {self.results.get('auto_match_rate', 0):.1%}")
        print(f"- Unmatched transactions: {self.results.get('unmatched_txns', 0)}")
        
        # Match type breakdown from API
        match_type_counts = self.results.get('match_type_counts', {})\n        print(f"\\nMatch Type Distribution (API Results):")
        for match_type, count in match_type_counts.items():
            percentage = count / total_txns * 100 if total_txns > 0 else 0
            print(f"- {match_type.capitalize()}: {count} ({percentage:.1f}%)")
        
        # Ground truth analysis
        expected_by_type = {}
        for txn in self.ground_truth['transactions'].values():
            match_type = txn['expected_match_type']
            expected_by_type[match_type] = expected_by_type.get(match_type, 0) + 1
        
        print(f"\\nExpected Match Type Distribution (Ground Truth):")
        for match_type, count in expected_by_type.items():
            percentage = count / total_txns * 100 if total_txns > 0 else 0
            print(f"- {match_type.capitalize()}: {count} ({percentage:.1f}%)")
        
        # Accuracy analysis
        print(f"\\nAccuracy Analysis:")
        correct_matches = 0
        type_accuracy = {}
        
        # Create lookup for easy matching
        match_lookup = {}
        for match in matches:
            txn_id = match['txn_id']
            match_lookup[txn_id] = match
        
        for txn_id, txn_data in self.ground_truth['transactions'].items():
            expected_type = txn_data['expected_match_type']
            
            if expected_type not in type_accuracy:
                type_accuracy[expected_type] = {'total': 0, 'correct': 0, 'found': 0}
            
            type_accuracy[expected_type]['total'] += 1
            
            if txn_id in match_lookup:
                actual_match = match_lookup[txn_id]
                actual_type = actual_match['match_type']
                type_accuracy[expected_type]['found'] += 1
                
                # Check if match type is correct
                if actual_type == expected_type:
                    correct_matches += 1
                    type_accuracy[expected_type]['correct'] += 1
                else:
                    print(f"  Mismatch: TXN {txn_id} expected {expected_type}, got {actual_type}")
            else:
                # Transaction not matched
                if expected_type == 'unmatched':
                    correct_matches += 1
                    type_accuracy[expected_type]['correct'] += 1
        
        overall_accuracy = correct_matches / total_txns if total_txns > 0 else 0
        print(f"\\nOverall Accuracy: {correct_matches}/{total_txns} ({overall_accuracy:.1%})")
        
        print(f"\\nAccuracy by Match Type:")
        for match_type, stats in type_accuracy.items():
            if stats['total'] > 0:
                recall = stats['found'] / stats['total']
                precision = stats['correct'] / stats['found'] if stats['found'] > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                
                print(f"- {match_type.capitalize()}:")
                print(f"  Recall: {stats['found']}/{stats['total']} ({recall:.1%})")
                print(f"  Precision: {stats['correct']}/{stats['found']} ({precision:.1%})")
                print(f"  F1-Score: {f1:.3f}")
        
        # Score distribution analysis
        if matches:
            scores = [match['score'] for match in matches]
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            
            print(f"\\nScore Distribution:")
            print(f"- Average score: {avg_score:.3f}")
            print(f"- Min score: {min_score:.3f}")
            print(f"- Max score: {max_score:.3f}")
            
            # Score by match type
            score_by_type = {}
            for match in matches:
                match_type = match['match_type']
                if match_type not in score_by_type:
                    score_by_type[match_type] = []
                score_by_type[match_type].append(match['score'])
            
            print(f"\\nAverage Score by Match Type:")
            for match_type, type_scores in score_by_type.items():
                avg = sum(type_scores) / len(type_scores)
                print(f"- {match_type.capitalize()}: {avg:.3f}")
        
        return {
            'overall_accuracy': overall_accuracy,
            'total_transactions': total_txns,
            'matches_found': len(matches),
            'match_rate': len(matches) / total_txns,
            'auto_match_rate': self.results.get('auto_match_rate', 0),
            'type_accuracy': type_accuracy,
            'expected_distribution': expected_by_type,
            'actual_distribution': match_type_counts
        }
    
    def test_parameter_sensitivity(self):
        """Test sensitivity to different parameter settings"""
        print(f"\\n" + "="*60)
        print("PARAMETER SENSITIVITY ANALYSIS")
        print("="*60)
        
        # Test configurations
        configs = [
            {
                "name": "Conservative",
                "config": {
                    "amount_tolerance": 0.01,
                    "date_window_days": 3,
                    "fuzzy_threshold": 0.9,
                    "partial_max_txns": 2,
                    "weights": {"exact": 0.7, "windowed": 0.2, "fuzzy": 0.1, "partial": 0.0}
                }
            },
            {
                "name": "Aggressive", 
                "config": {
                    "amount_tolerance": 0.05,
                    "date_window_days": 10,
                    "fuzzy_threshold": 0.7,
                    "partial_max_txns": 4,
                    "weights": {"exact": 0.3, "windowed": 0.2, "fuzzy": 0.3, "partial": 0.2}
                }
            },
            {
                "name": "Fuzzy-focused",
                "config": {
                    "amount_tolerance": 0.02,
                    "date_window_days": 7,
                    "fuzzy_threshold": 0.8,
                    "partial_max_txns": 3,
                    "weights": {"exact": 0.4, "windowed": 0.1, "fuzzy": 0.4, "partial": 0.1}
                }
            }
        ]
        
        results_comparison = []
        
        for test_config in configs:
            print(f"\\nTesting {test_config['name']} configuration...")
            
            api_result = self.call_reconciliation_api(test_config['config'])
            if api_result:
                self.results = api_result
                evaluation = self.evaluate_performance()
                
                if evaluation:
                    results_comparison.append({
                        'name': test_config['name'],
                        'config': test_config['config'],
                        'results': evaluation
                    })
        
        # Compare results
        if results_comparison:
            print(f"\\n" + "="*60)
            print("CONFIGURATION COMPARISON")
            print("="*60)
            print(f"{'Configuration':<15} {'Match Rate':<12} {'Auto-Match':<12} {'Accuracy':<10}")
            print("-" * 60)
            
            for result in results_comparison:
                name = result['name']
                match_rate = result['results']['match_rate']
                auto_rate = result['results']['auto_match_rate'] 
                accuracy = result['results']['overall_accuracy']
                
                print(f"{name:<15} {match_rate:<12.1%} {auto_rate:<12.1%} {accuracy:<10.1%}")
        
        return results_comparison


def main():
    """Main evaluation script"""
    print("Reconciliation Engine Evaluation")
    print("="*50)
    
    # Check if synthetic data files exist
    txn_file = "synthetic_transactions.csv"
    ledger_file = "synthetic_ledger_entries.csv"
    
    if not os.path.exists(txn_file) or not os.path.exists(ledger_file):
        print(f"Error: Synthetic data files not found!")
        print(f"Please run gen_synth_recon.py first to generate test data.")
        print(f"Expected files: {txn_file}, {ledger_file}")
        sys.exit(1)
    
    # Initialize evaluator
    evaluator = ReconciliationEvaluator()
    
    # Load ground truth data
    if not evaluator.load_ground_truth(txn_file, ledger_file):
        print("Failed to load ground truth data")
        sys.exit(1)
    
    # Test default configuration
    print(f"\\nTesting default configuration...")
    api_result = evaluator.call_reconciliation_api()
    
    if not api_result:
        print("Failed to call reconciliation API")
        print("Make sure the backend server is running on http://localhost:8000")
        sys.exit(1)
    
    # Evaluate performance
    evaluation = evaluator.evaluate_performance()
    
    if not evaluation:
        print("Failed to evaluate performance")
        sys.exit(1)
    
    # Test parameter sensitivity (optional)
    if len(sys.argv) > 1 and sys.argv[1] == "--sensitivity":
        evaluator.test_parameter_sensitivity()
    
    print(f"\\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"\\nRun with --sensitivity flag to test different parameter configurations")
    print(f"Example: python eval_recon.py --sensitivity")


if __name__ == "__main__":
    main()