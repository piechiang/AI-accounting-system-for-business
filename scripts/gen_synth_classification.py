#!/usr/bin/env python3
"""
Generate Synthetic Classification Test Data

Creates 200 synthetic transaction samples for testing the classification pipeline.
Includes diverse transaction types with known ground truth labels.
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Transaction templates with known patterns
TRANSACTION_TEMPLATES = [
    # Office Supplies
    {
        'category': 'Office Expenses',
        'coa_code': '5000',
        'patterns': [
            'STAPLES {location}',
            'OFFICE DEPOT {location}',
            'AMAZON OFFICE SUPPLIES',
            'BEST BUY OFFICE',
            'OFFICEMAX {location}',
            'COSTCO OFFICE SUPPLIES',
            'WALMART SUPPLIES',
            'TARGET OFFICE SECTION'
        ],
        'amount_range': (15.99, 299.99),
        'vendors': ['STAPLES', 'OFFICE DEPOT', 'AMAZON', 'BEST BUY', 'OFFICEMAX', 'COSTCO']
    },
    
    # Software & Subscriptions
    {
        'category': 'Software Expenses',
        'coa_code': '5300',
        'patterns': [
            'MICROSOFT CORP SUBSCRIPTION',
            'ADOBE CREATIVE CLOUD',
            'GOOGLE WORKSPACE',
            'ZOOM VIDEO COMMUNICATIONS',
            'SLACK TECHNOLOGIES',
            'GITHUB INC',
            'DROPBOX SUBSCRIPTION',
            'ATLASSIAN JIRA',
            'SALESFORCE.COM',
            'QUICKBOOKS ONLINE'
        ],
        'amount_range': (9.99, 149.99),
        'vendors': ['MICROSOFT', 'ADOBE', 'GOOGLE', 'ZOOM', 'SLACK', 'GITHUB', 'DROPBOX']
    },
    
    # Travel Expenses
    {
        'category': 'Travel Expenses',
        'coa_code': '5400',
        'patterns': [
            'AMERICAN AIRLINES',
            'DELTA AIR LINES',
            'SOUTHWEST AIRLINES',
            'UBER RIDE {location}',
            'LYFT RIDE {location}',
            'MARRIOTT HOTEL {location}',
            'HILTON HOTELS {location}',
            'HERTZ RENTAL CAR',
            'ENTERPRISE RENT-A-CAR',
            'AIRBNB {location}'
        ],
        'amount_range': (25.50, 899.99),
        'vendors': ['AMERICAN', 'DELTA', 'SOUTHWEST', 'UBER', 'LYFT', 'MARRIOTT', 'HILTON']
    },
    
    # Meals & Entertainment
    {
        'category': 'Meals & Entertainment',
        'coa_code': '5200',
        'patterns': [
            'STARBUCKS {location}',
            'MCDONALDS {location}',
            'SUBWAY {location}',
            'PIZZA HUT {location}',
            'DOMINOS PIZZA {location}',
            'CHIPOTLE {location}',
            'PANERA BREAD {location}',
            'OLIVE GARDEN {location}',
            'APPLEBEES {location}',
            'LOCAL RESTAURANT'
        ],
        'amount_range': (8.99, 156.78),
        'vendors': ['STARBUCKS', 'MCDONALD', 'SUBWAY', 'PIZZA', 'DOMINOS', 'CHIPOTLE']
    },
    
    # Vehicle Expenses
    {
        'category': 'Vehicle Expenses',
        'coa_code': '5100',
        'patterns': [
            'SHELL GAS STATION {location}',
            'EXXON MOBIL {location}',
            'CHEVRON {location}',
            'BP GAS STATION {location}',
            'MARATHON PETROLEUM',
            'VALERO GAS {location}',
            'SPEEDWAY GAS {location}',
            'JIFFY LUBE {location}',
            'AUTO ZONE {location}',
            'ADVANCE AUTO PARTS'
        ],
        'amount_range': (25.00, 89.99),
        'vendors': ['SHELL', 'EXXON', 'CHEVRON', 'BP', 'MARATHON', 'VALERO']
    },
    
    # Equipment & Hardware
    {
        'category': 'Equipment Expenses',
        'coa_code': '5500',
        'patterns': [
            'DELL COMPUTER',
            'HP ENTERPRISE',
            'LENOVO SYSTEMS',
            'APPLE STORE {location}',
            'BEST BUY COMPUTERS',
            'AMAZON ELECTRONICS',
            'NEWEGG HARDWARE',
            'MICRO CENTER {location}',
            'STAPLES TECHNOLOGY',
            'CDW CORPORATION'
        ],
        'amount_range': (199.99, 2499.99),
        'vendors': ['DELL', 'HP', 'LENOVO', 'APPLE', 'BEST BUY', 'AMAZON']
    },
    
    # Professional Services
    {
        'category': 'Professional Services',
        'coa_code': '5600',
        'patterns': [
            'LEGAL SERVICES LLC',
            'ACCOUNTING FIRM {location}',
            'CONSULTING GROUP',
            'MARKETING AGENCY',
            'DESIGN STUDIO',
            'IT SERVICES {location}',
            'PROFESSIONAL SERVICES',
            'BUSINESS CONSULTANT',
            'TAX PREPARATION',
            'AUDIT SERVICES'
        ],
        'amount_range': (150.00, 5000.00),
        'vendors': ['LEGAL', 'ACCOUNTING', 'CONSULTING', 'MARKETING', 'DESIGN']
    },
    
    # Utilities
    {
        'category': 'Utilities',
        'coa_code': '5700',
        'patterns': [
            'ELECTRIC COMPANY {location}',
            'GAS UTILITY {location}',
            'WATER DEPARTMENT',
            'INTERNET SERVICE PROVIDER',
            'PHONE COMPANY',
            'COMCAST BUSINESS',
            'VERIZON BUSINESS',
            'AT&T BUSINESS',
            'WASTE MANAGEMENT',
            'CITY UTILITIES'
        ],
        'amount_range': (45.99, 299.99),
        'vendors': ['ELECTRIC', 'GAS', 'WATER', 'COMCAST', 'VERIZON', 'ATT']
    }
]

LOCATIONS = [
    'NYC', 'LA', 'CHICAGO', 'HOUSTON', 'PHOENIX', 'PHILADELPHIA', 'SAN ANTONIO',
    'SAN DIEGO', 'DALLAS', 'SAN JOSE', 'AUSTIN', 'JACKSONVILLE', 'FORT WORTH',
    'COLUMBUS', 'CHARLOTTE', 'SEATTLE', 'DENVER', 'BOSTON', 'EL PASO', 'WASHINGTON'
]

COMPLEXITY_MODIFIERS = [
    # Add noise to make classification more realistic
    'CORP', 'INC', 'LLC', 'CO', 'LTD', 'GROUP', 'SERVICES', 'SOLUTIONS',
    'SYSTEMS', 'TECHNOLOGIES', 'ENTERPRISES', 'HOLDINGS', 'INTERNATIONAL'
]

def generate_transaction_description(template: Dict[str, Any]) -> tuple[str, str, float]:
    """Generate a realistic transaction description with vendor and amount"""
    
    # Select random pattern
    pattern = random.choice(template['patterns'])
    
    # Replace location placeholder if present
    if '{location}' in pattern:
        location = random.choice(LOCATIONS)
        pattern = pattern.replace('{location}', location)
    
    # Add random complexity modifier sometimes
    if random.random() < 0.3:
        modifier = random.choice(COMPLEXITY_MODIFIERS)
        pattern = f"{pattern} {modifier}"
    
    # Generate amount within range
    min_amt, max_amt = template['amount_range']
    amount = round(random.uniform(min_amt, max_amt), 2)
    
    # Extract vendor (first word typically)
    vendor = pattern.split()[0]
    
    return pattern, vendor, amount

def generate_transaction_date() -> str:
    """Generate random transaction date within last 90 days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Random date between start and end
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime('%Y-%m-%d')

def add_classification_noise(transactions: List[Dict[str, Any]], noise_ratio: float = 0.1) -> List[Dict[str, Any]]:
    """Add some ambiguous/edge case transactions to make evaluation more realistic"""
    
    noisy_transactions = []
    num_noisy = int(len(transactions) * noise_ratio)
    
    ambiguous_patterns = [
        # Could be office supplies or equipment
        {
            'description': 'AMAZON PURCHASE BUSINESS',
            'vendor': 'AMAZON',
            'category': 'Office Expenses',
            'coa_code': '5000',
            'amount_range': (50, 200),
            'note': 'Ambiguous - could be office supplies or equipment'
        },
        # Could be meals or office supplies
        {
            'description': 'WALMART BUSINESS PURCHASE',
            'vendor': 'WALMART',
            'category': 'Office Expenses', 
            'coa_code': '5000',
            'amount_range': (25, 100),
            'note': 'Ambiguous - could be supplies or food'
        },
        # Could be travel or vehicle
        {
            'description': 'SHELL TRAVEL CENTER',
            'vendor': 'SHELL',
            'category': 'Travel Expenses',
            'coa_code': '5400',
            'amount_range': (30, 80),
            'note': 'Ambiguous - travel stop vs regular gas'
        },
        # Could be software or professional services
        {
            'description': 'TECH CONSULTING SERVICES',
            'vendor': 'TECH',
            'category': 'Professional Services',
            'coa_code': '5600',
            'amount_range': (500, 2000),
            'note': 'Ambiguous - consulting vs software'
        }
    ]
    
    for i in range(num_noisy):
        pattern = random.choice(ambiguous_patterns)
        amount = round(random.uniform(*pattern['amount_range']), 2)
        
        noisy_transaction = {
            'id': len(transactions) + i + 1,
            'date': generate_transaction_date(),
            'description': pattern['description'],
            'vendor': pattern['vendor'],
            'amount': -amount,  # Negative for expenses
            'category': pattern['category'],
            'coa_code': pattern['coa_code'],
            'confidence_expected': random.uniform(0.6, 0.8),  # Lower confidence for ambiguous
            'notes': pattern['note'],
            'is_ambiguous': True
        }
        noisy_transactions.append(noisy_transaction)
    
    return noisy_transactions

def generate_synthetic_data(num_samples: int = 200) -> List[Dict[str, Any]]:
    """Generate synthetic transaction data for classification testing"""
    
    transactions = []
    
    # Calculate samples per category (roughly equal distribution)
    samples_per_category = num_samples // len(TRANSACTION_TEMPLATES)
    remaining_samples = num_samples % len(TRANSACTION_TEMPLATES)
    
    transaction_id = 1
    
    for i, template in enumerate(TRANSACTION_TEMPLATES):
        # Determine number of samples for this category
        category_samples = samples_per_category
        if i < remaining_samples:
            category_samples += 1
        
        for j in range(category_samples):
            description, vendor, amount = generate_transaction_description(template)
            
            transaction = {
                'id': transaction_id,
                'date': generate_transaction_date(),
                'description': description,
                'vendor': vendor,
                'amount': -amount,  # Negative for expenses
                'category': template['category'],
                'coa_code': template['coa_code'],
                'confidence_expected': random.uniform(0.85, 0.95),  # High confidence for clear patterns
                'notes': f"Generated from template: {template['category']}",
                'is_ambiguous': False
            }
            
            transactions.append(transaction)
            transaction_id += 1
    
    # Add some noisy/ambiguous transactions
    noisy_transactions = add_classification_noise(transactions, noise_ratio=0.15)
    transactions.extend(noisy_transactions)
    
    # Shuffle to mix categories
    random.shuffle(transactions)
    
    # Update IDs to be sequential
    for i, txn in enumerate(transactions, 1):
        txn['id'] = i
    
    return transactions

def save_to_csv(transactions: List[Dict[str, Any]], filename: str):
    """Save transactions to CSV file"""
    
    fieldnames = [
        'id', 'date', 'description', 'vendor', 'amount', 
        'category', 'coa_code', 'confidence_expected', 'notes', 'is_ambiguous'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

def save_to_json(transactions: List[Dict[str, Any]], filename: str):
    """Save transactions to JSON file"""
    
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_samples': len(transactions),
            'categories': list(set(txn['category'] for txn in transactions)),
            'date_range': {
                'start': min(txn['date'] for txn in transactions),
                'end': max(txn['date'] for txn in transactions)
            }
        },
        'transactions': transactions
    }
    
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(output, jsonfile, indent=2, default=str)

def generate_statistics(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate statistics about the synthetic data"""
    
    categories = {}
    total_amount = 0
    ambiguous_count = 0
    
    for txn in transactions:
        category = txn['category']
        if category not in categories:
            categories[category] = {'count': 0, 'total_amount': 0}
        
        categories[category]['count'] += 1
        categories[category]['total_amount'] += abs(txn['amount'])
        total_amount += abs(txn['amount'])
        
        if txn.get('is_ambiguous', False):
            ambiguous_count += 1
    
    # Calculate percentages
    for category_data in categories.values():
        category_data['percentage'] = (category_data['count'] / len(transactions)) * 100
        category_data['avg_amount'] = category_data['total_amount'] / category_data['count']
    
    stats = {
        'total_transactions': len(transactions),
        'total_amount': total_amount,
        'avg_amount': total_amount / len(transactions),
        'ambiguous_transactions': ambiguous_count,
        'ambiguous_percentage': (ambiguous_count / len(transactions)) * 100,
        'categories': categories
    }
    
    return stats

def print_statistics(stats: Dict[str, Any]):
    """Print statistics to console"""
    
    print("\\n" + "="*60)
    print("SYNTHETIC CLASSIFICATION DATA STATISTICS")
    print("="*60)
    
    print(f"Total Transactions: {stats['total_transactions']}")
    print(f"Total Amount: ${stats['total_amount']:,.2f}")
    print(f"Average Amount: ${stats['avg_amount']:.2f}")
    print(f"Ambiguous Transactions: {stats['ambiguous_transactions']} ({stats['ambiguous_percentage']:.1f}%)")
    
    print("\\nCategory Breakdown:")
    print("-" * 60)
    print(f"{'Category':<25} {'Count':<8} {'%':<8} {'Avg Amount':<12}")
    print("-" * 60)
    
    for category, data in stats['categories'].items():
        print(f"{category:<25} {data['count']:<8} {data['percentage']:<8.1f} ${data['avg_amount']:<11.2f}")
    
    print("-" * 60)

def main():
    """Main function to generate synthetic classification data"""
    
    # Set random seed for reproducibility
    random.seed(42)
    
    print("Generating synthetic classification test data...")
    
    # Generate transactions
    transactions = generate_synthetic_data(num_samples=200)
    
    # Create output directory
    output_dir = Path("datasets")
    output_dir.mkdir(exist_ok=True)
    
    # Save in multiple formats
    csv_file = output_dir / "synthetic_classification_data.csv"
    json_file = output_dir / "synthetic_classification_data.json"
    
    save_to_csv(transactions, csv_file)
    save_to_json(transactions, json_file)
    
    # Generate and print statistics
    stats = generate_statistics(transactions)
    print_statistics(stats)
    
    print(f"\\nData saved to:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")
    
    # Save statistics
    stats_file = output_dir / "synthetic_classification_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"  Stats: {stats_file}")
    print("\\nSynthetic data generation complete!")

if __name__ == "__main__":
    main()