#!/usr/bin/env python3
"""
Generate synthetic reconciliation data for testing.
Creates transactions and ledger entries with known matching patterns.
"""

import random
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from typing import List, Dict, Any

# Fixed seed for reproducible results
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

class SyntheticDataGenerator:
    """Generate synthetic transaction and ledger data for reconciliation testing"""
    
    def __init__(self):
        self.transaction_counter = 1
        self.ledger_counter = 1
        
        # Common transaction descriptions
        self.descriptions = [
            "Coffee shop purchase",
            "Office supplies expense", 
            "Client payment received",
            "Utility bill payment",
            "Software subscription",
            "Travel reimbursement",
            "Marketing campaign cost",
            "Equipment purchase",
            "Consultant fee payment",
            "Insurance premium"
        ]
        
        # Counterparties
        self.counterparties = [
            "Starbucks", "Office Depot", "ABC Corp", "PG&E",
            "Microsoft", "Delta Airlines", "Google Ads", "Apple",
            "Consulting LLC", "State Farm"
        ]
    
    def generate_amount(self, min_amount=10.0, max_amount=5000.0) -> Decimal:
        """Generate random amount"""
        return Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
    
    def generate_date(self, start_date=None, days_range=30) -> datetime:
        """Generate random date within range"""
        if start_date is None:
            start_date = datetime(2024, 1, 1)
        
        days_offset = random.randint(0, days_range)
        return start_date + timedelta(days=days_offset)
    
    def add_noise_to_description(self, desc: str) -> str:
        """Add realistic noise to descriptions"""
        noise_types = [
            lambda x: f"{x} - TXN#{random.randint(100000, 999999)}",
            lambda x: f"{x} {datetime.now().strftime('%Y-%m-%d')}",
            lambda x: f"Payment for {x}",
            lambda x: f"{x} (Online)",
            lambda x: x.upper(),
            lambda x: x.replace(" ", "_"),
        ]
        
        if random.random() < 0.3:  # 30% chance of noise
            return random.choice(noise_types)(desc)
        return desc
    
    def generate_exact_matches(self, count=50) -> List[Dict[str, Any]]:
        """Generate exact match pairs (same amount, date within 1 day)"""
        pairs = []
        
        for i in range(count):
            amount = self.generate_amount()
            base_date = self.generate_date()
            desc = random.choice(self.descriptions)
            
            # Transaction
            txn_date = base_date
            txn = {
                'id': self.transaction_counter,
                'amount_base': amount,
                'transaction_date': txn_date,
                'description_normalized': self.add_noise_to_description(desc),
                'counterparty_normalized': random.choice(self.counterparties),
                'match_type': 'exact'
            }
            
            # Matching ledger entry (same day or 1 day diff)
            ledger_date = base_date + timedelta(days=random.choice([0, 1, -1]))
            ledger = {
                'id': self.ledger_counter,
                'amount_base': amount,
                'entry_date': ledger_date,
                'memo': desc,
                'reference': f"REF-{self.ledger_counter:06d}",
                'is_reconciled': 'false'
            }
            
            pairs.append({'transaction': txn, 'ledger': ledger})
            self.transaction_counter += 1
            self.ledger_counter += 1
        
        return pairs
    
    def generate_windowed_matches(self, count=30) -> List[Dict[str, Any]]:
        """Generate windowed match pairs (same amount, date within 5 days)"""
        pairs = []
        
        for i in range(count):
            amount = self.generate_amount()
            base_date = self.generate_date()
            desc = random.choice(self.descriptions)
            
            # Transaction
            txn = {
                'id': self.transaction_counter,
                'amount_base': amount,
                'transaction_date': base_date,
                'description_normalized': self.add_noise_to_description(desc),
                'counterparty_normalized': random.choice(self.counterparties),
                'match_type': 'windowed'
            }
            
            # Matching ledger entry (2-5 days difference)
            date_diff = random.choice([2, 3, 4, 5, -2, -3, -4, -5])
            ledger_date = base_date + timedelta(days=date_diff)
            ledger = {
                'id': self.ledger_counter,
                'amount_base': amount,
                'entry_date': ledger_date,
                'memo': desc,
                'reference': f"REF-{self.ledger_counter:06d}",
                'is_reconciled': 'false'
            }
            
            pairs.append({'transaction': txn, 'ledger': ledger})
            self.transaction_counter += 1
            self.ledger_counter += 1
        
        return pairs
    
    def generate_fuzzy_matches(self, count=40) -> List[Dict[str, Any]]:
        """Generate fuzzy match pairs (similar descriptions, close amounts)"""
        pairs = []
        
        for i in range(count):
            base_amount = self.generate_amount()
            base_date = self.generate_date()
            base_desc = random.choice(self.descriptions)
            
            # Transaction
            txn_amount = base_amount + Decimal(str(round(random.uniform(-5, 5), 2)))
            txn = {
                'id': self.transaction_counter,
                'amount_base': txn_amount,
                'transaction_date': base_date,
                'description_normalized': self.add_noise_to_description(base_desc),
                'counterparty_normalized': random.choice(self.counterparties),
                'match_type': 'fuzzy'
            }
            
            # Similar ledger entry with slight variations
            ledger_amount = base_amount + Decimal(str(round(random.uniform(-3, 3), 2)))
            ledger_date = base_date + timedelta(days=random.randint(-10, 10))
            
            # Create similar description
            variations = [
                base_desc,
                base_desc.replace("purchase", "buy"),
                base_desc.replace("payment", "pay"),
                f"{base_desc} expense",
                f"Monthly {base_desc}",
                base_desc.replace(" ", "-"),
            ]
            
            ledger = {
                'id': self.ledger_counter,
                'amount_base': ledger_amount,
                'entry_date': ledger_date,
                'memo': random.choice(variations),
                'reference': f"REF-{self.ledger_counter:06d}",
                'is_reconciled': 'false'
            }
            
            pairs.append({'transaction': txn, 'ledger': ledger})
            self.transaction_counter += 1
            self.ledger_counter += 1
        
        return pairs
    
    def generate_partial_matches(self, count=20) -> List[Dict[str, Any]]:
        """Generate partial match sets (1 transaction = sum of multiple ledger entries)"""
        groups = []
        
        for i in range(count):
            total_amount = self.generate_amount(100, 1000)
            base_date = self.generate_date()
            desc = random.choice(self.descriptions)
            
            # Transaction
            txn = {
                'id': self.transaction_counter,
                'amount_base': total_amount,
                'transaction_date': base_date,
                'description_normalized': self.add_noise_to_description(desc),
                'counterparty_normalized': random.choice(self.counterparties),
                'match_type': 'partial'
            }
            
            # Split into 2-3 ledger entries
            num_parts = random.choice([2, 3])
            remaining = total_amount
            ledgers = []
            
            for j in range(num_parts):
                if j == num_parts - 1:  # Last part gets remainder
                    part_amount = remaining
                else:
                    max_part = remaining / (num_parts - j)
                    min_part = max_part * Decimal('0.3')
                    part_amount = Decimal(str(round(random.uniform(float(min_part), float(max_part)), 2)))
                    remaining -= part_amount
                
                ledger_date = base_date + timedelta(days=random.randint(0, 2))
                ledger = {
                    'id': self.ledger_counter,
                    'amount_base': part_amount,
                    'entry_date': ledger_date,
                    'memo': f"{desc} - Part {j+1}",
                    'reference': f"REF-{self.ledger_counter:06d}",
                    'is_reconciled': 'false'
                }
                
                ledgers.append(ledger)
                self.ledger_counter += 1
            
            groups.append({'transaction': txn, 'ledgers': ledgers})
            self.transaction_counter += 1
        
        return groups
    
    def generate_unmatched_data(self, txn_count=25, ledger_count=25) -> Dict[str, List]:
        """Generate unmatched transactions and ledger entries"""
        unmatched_txns = []
        unmatched_ledgers = []
        
        # Unmatched transactions
        for i in range(txn_count):
            txn = {
                'id': self.transaction_counter,
                'amount_base': self.generate_amount(),
                'transaction_date': self.generate_date(),
                'description_normalized': self.add_noise_to_description(random.choice(self.descriptions)),
                'counterparty_normalized': random.choice(self.counterparties),
                'match_type': 'unmatched'
            }
            unmatched_txns.append(txn)
            self.transaction_counter += 1
        
        # Unmatched ledger entries
        for i in range(ledger_count):
            ledger = {
                'id': self.ledger_counter,
                'amount_base': self.generate_amount(),
                'entry_date': self.generate_date(),
                'memo': random.choice(self.descriptions),
                'reference': f"REF-{self.ledger_counter:06d}",
                'is_reconciled': 'false'
            }
            unmatched_ledgers.append(ledger)
            self.ledger_counter += 1
        
        return {'transactions': unmatched_txns, 'ledgers': unmatched_ledgers}
    
    def export_to_csv(self, data: Dict[str, Any], output_dir="./"):
        """Export generated data to CSV files"""
        # Transactions
        txn_file = f"{output_dir}synthetic_transactions.csv"
        with open(txn_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'amount_base', 'transaction_date', 'description_normalized', 
                           'counterparty_normalized', 'expected_match_type'])
            
            for match_type, matches in data.items():
                if match_type == 'unmatched':
                    for txn in matches['transactions']:
                        writer.writerow([
                            txn['id'], txn['amount_base'], txn['transaction_date'].isoformat(),
                            txn['description_normalized'], txn['counterparty_normalized'], 
                            txn['match_type']
                        ])
                elif match_type == 'partial':
                    for group in matches:
                        txn = group['transaction']
                        writer.writerow([
                            txn['id'], txn['amount_base'], txn['transaction_date'].isoformat(),
                            txn['description_normalized'], txn['counterparty_normalized'], 
                            txn['match_type']
                        ])
                else:
                    for pair in matches:
                        txn = pair['transaction']
                        writer.writerow([
                            txn['id'], txn['amount_base'], txn['transaction_date'].isoformat(),
                            txn['description_normalized'], txn['counterparty_normalized'], 
                            txn['match_type']
                        ])
        
        # Ledger entries
        ledger_file = f"{output_dir}synthetic_ledger_entries.csv"
        with open(ledger_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'amount_base', 'entry_date', 'memo', 'reference', 'is_reconciled'])
            
            for match_type, matches in data.items():
                if match_type == 'unmatched':
                    for ledger in matches['ledgers']:
                        writer.writerow([
                            ledger['id'], ledger['amount_base'], ledger['entry_date'].isoformat(),
                            ledger['memo'], ledger['reference'], ledger['is_reconciled']
                        ])
                elif match_type == 'partial':
                    for group in matches:
                        for ledger in group['ledgers']:
                            writer.writerow([
                                ledger['id'], ledger['amount_base'], ledger['entry_date'].isoformat(),
                                ledger['memo'], ledger['reference'], ledger['is_reconciled']
                            ])
                else:
                    for pair in matches:
                        ledger = pair['ledger']
                        writer.writerow([
                            ledger['id'], ledger['amount_base'], ledger['entry_date'].isoformat(),
                            ledger['memo'], ledger['reference'], ledger['is_reconciled']
                        ])
        
        return txn_file, ledger_file


def main():
    """Generate synthetic reconciliation data"""
    print(f"Generating synthetic reconciliation data with seed {RANDOM_SEED}")
    
    generator = SyntheticDataGenerator()
    
    # Generate different types of matches
    data = {
        'exact': generator.generate_exact_matches(50),
        'windowed': generator.generate_windowed_matches(30), 
        'fuzzy': generator.generate_fuzzy_matches(40),
        'partial': generator.generate_partial_matches(20),
        'unmatched': generator.generate_unmatched_data(25, 25)
    }
    
    # Export to CSV
    txn_file, ledger_file = generator.export_to_csv(data)
    
    # Print summary
    print(f"\nSynthetic data generated:")
    print(f"- Exact matches: {len(data['exact'])} pairs")
    print(f"- Windowed matches: {len(data['windowed'])} pairs") 
    print(f"- Fuzzy matches: {len(data['fuzzy'])} pairs")
    print(f"- Partial matches: {len(data['partial'])} groups")
    print(f"- Unmatched transactions: {len(data['unmatched']['transactions'])}")
    print(f"- Unmatched ledger entries: {len(data['unmatched']['ledgers'])}")
    print(f"\nFiles created:")
    print(f"- {txn_file}")
    print(f"- {ledger_file}")
    
    # Calculate totals
    total_txns = (len(data['exact']) + len(data['windowed']) + 
                  len(data['fuzzy']) + len(data['partial']) + 
                  len(data['unmatched']['transactions']))
    total_ledgers = (len(data['exact']) + len(data['windowed']) + 
                     len(data['fuzzy']) + 
                     sum(len(group['ledgers']) for group in data['partial']) +
                     len(data['unmatched']['ledgers']))
    
    print(f"\nTotals:")
    print(f"- Total transactions: {total_txns}")
    print(f"- Total ledger entries: {total_ledgers}")
    
    # Expected match rates
    matchable_txns = total_txns - len(data['unmatched']['transactions'])
    auto_matchable = len(data['exact']) + len(data['windowed'])
    
    print(f"\nExpected performance:")
    print(f"- Overall match rate: {matchable_txns/total_txns:.1%}")
    print(f"- Auto-match rate: {auto_matchable/total_txns:.1%}")


if __name__ == "__main__":
    main()