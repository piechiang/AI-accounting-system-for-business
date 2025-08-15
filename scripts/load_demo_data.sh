#!/bin/bash

# AI Accounting Assistant - Demo Data Loader
echo "📊 Loading Demo Data..."
echo "======================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_success() {
    echo -e "${BLUE}[SUCCESS]${NC} $1"
}

API_BASE="http://localhost:8000/api/v1"

# Check if backend is running
print_info "Checking if backend is running..."
if ! curl -s "$API_BASE/health" > /dev/null; then
    print_warning "Backend is not running. Please start it first with: ./scripts/start.sh"
    exit 1
fi

print_success "Backend is running!"

# Load Chart of Accounts
print_info "Loading Chart of Accounts..."
curl -X POST "$API_BASE/accounts/import" \
    -F "file=@datasets/chart_of_accounts.csv" \
    -s -o /dev/null
print_success "Chart of Accounts loaded"

# Load Classification Rules
print_info "Loading Classification Rules..."
curl -X POST "$API_BASE/classification/rules/import" \
    -F "file=@datasets/classification_rules.csv" \
    -s -o /dev/null
print_success "Classification Rules loaded"

# Load Bank Statement
print_info "Loading Bank Statement..."
curl -X POST "$API_BASE/transactions/upload" \
    -F "file=@datasets/sample_bank_statement.csv" \
    -F "source=bank_statement" \
    -s -o /dev/null
print_success "Bank Statement loaded"

# Load Credit Card Transactions
print_info "Loading Credit Card Transactions..."
curl -X POST "$API_BASE/transactions/upload" \
    -F "file=@datasets/sample_credit_card.csv" \
    -F "source=credit_card" \
    -s -o /dev/null
print_success "Credit Card Transactions loaded"

# Run Classification
print_info "Running AI Classification..."
curl -X POST "$API_BASE/classification/classify_all" \
    -H "Content-Type: application/json" \
    -s -o /dev/null
print_success "AI Classification completed"

# Run Reconciliation
print_info "Running Auto Reconciliation..."
curl -X POST "$API_BASE/reconciliation/auto_reconcile" \
    -H "Content-Type: application/json" \
    -s -o /dev/null
print_success "Auto Reconciliation completed"

echo ""
print_success "🎉 Demo data loaded successfully!"
echo ""
echo "You can now:"
echo "- View transactions at: http://localhost:5173/transactions"
echo "- Check classification at: http://localhost:5173/classification"
echo "- Review reconciliation at: http://localhost:5173/reconciliation"
echo "- See dashboard at: http://localhost:5173/dashboard"
echo "- Export data at: http://localhost:5173/export"