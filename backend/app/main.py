from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.routers import (
    transactions, 
    classification, 
    reconciliation, 
    dashboard,
    export,
    tax_forms
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_db()
    yield

app = FastAPI(
    title="AI Accounting Assistant",
    description="智能财务助手：费用自动分类 + 银行对账 + 可视化仪表盘",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(classification.router, prefix="/api/v1/classification", tags=["classification"])
app.include_router(reconciliation.router, prefix="/api/v1/reconciliation", tags=["reconciliation"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(tax_forms.router, prefix="/api/v1/tax-forms", tags=["tax-forms"])

@app.get("/")
async def root():
    return {
        "message": "AI Accounting Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}