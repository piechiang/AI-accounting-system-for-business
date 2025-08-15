#!/bin/bash

# AI Accounting Assistant - Start Script
echo "🚀 Starting AI Accounting Assistant..."
echo "===================================="

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

print_url() {
    echo -e "${BLUE}[URL]${NC} $1"
}

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    print_warning "backend/.env file not found. Please run ./scripts/setup.sh first."
    exit 1
fi

# Function to kill background processes on exit
cleanup() {
    print_info "Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    print_info "Services stopped."
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Start backend
print_info "Starting FastAPI backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
print_info "Waiting for backend to start..."
sleep 3

# Start frontend
print_info "Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
print_info "Waiting for frontend to start..."
sleep 5

# Print access URLs
echo ""
print_info "✅ AI Accounting Assistant is now running!"
echo ""
print_url "Frontend (React):     http://localhost:5173"
print_url "Backend API:          http://localhost:8000"
print_url "API Documentation:    http://localhost:8000/docs"
print_url "API Redoc:            http://localhost:8000/redoc"
echo ""
print_info "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait