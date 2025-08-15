#!/bin/bash

# AI Accounting Assistant - Quick Setup Script
echo "🤖 AI Accounting Assistant - Quick Setup"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
print_status "Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

python_version=$(python3 --version | cut -d " " -f 2)
print_status "Python version: $python_version"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

node_version=$(node --version)
print_status "Node.js version: $node_version"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm."
    exit 1
fi

npm_version=$(npm --version)
print_status "npm version: $npm_version"

# Setup backend
print_status "Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cp .env.example .env
    print_warning "Please edit backend/.env file with your API keys before running the application!"
fi

# Setup database
print_status "Setting up database..."
if [ ! -f "ai_accounting.db" ]; then
    print_status "Creating SQLite database..."
    alembic upgrade head
fi

cd ..

# Setup frontend
print_status "Setting up frontend..."
cd frontend

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
npm install

cd ..

print_status "Setup completed successfully! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env file with your API keys"
echo "2. Run: ./scripts/start.sh"
echo ""
echo "For detailed instructions, see README.md"