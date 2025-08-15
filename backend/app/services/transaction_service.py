from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
import hashlib
from fastapi import UploadFile

from app.models.transactions import TransactionRaw, TransactionClean
from app.models.accounts import ChartOfAccounts
from app.services.data_cleaning_service import DataCleaningService

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.cleaning_service = DataCleaningService()

    async def process_upload(self, file: UploadFile, source: str) -> Dict[str, Any]:
        """Process uploaded transaction file"""
        # Read file into DataFrame
        file_content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("Unsupported file format. Please upload CSV or Excel files.")
        
        # Normalize column names for common formats
        df = self._normalize_columns(df, source)
        
        # Create transaction records
        new_count = 0
        duplicate_count = 0
        raw_transactions = []
        
        for _, row in df.iterrows():
            # Create transaction hash for deduplication
            hash_input = f"{row['date']}{row['amount']}{row['description']}{source}"
            transaction_hash = hashlib.md5(hash_input.encode()).hexdigest()
            
            # Check if transaction already exists
            existing = self.db.query(TransactionRaw).filter(
                TransactionRaw.transaction_hash == transaction_hash
            ).first()
            
            if existing:
                duplicate_count += 1
                continue
            
            # Create new transaction
            transaction = TransactionRaw(
                source=source,
                transaction_date=pd.to_datetime(row['date']),
                amount=float(row['amount']),
                currency=row.get('currency', 'USD'),
                description=row['description'],
                counterparty=row.get('counterparty'),
                reference=row.get('reference'),
                category_raw=row.get('category'),
                transaction_hash=transaction_hash
            )
            
            self.db.add(transaction)
            raw_transactions.append(transaction)
            new_count += 1
        
        self.db.commit()
        
        return {
            'total_count': len(df),
            'new_count': new_count,
            'duplicate_count': duplicate_count,
            'raw_transactions': raw_transactions
        }

    def _normalize_columns(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Normalize column names based on source"""
        column_mappings = {
            'bank': {
                'Date': 'date',
                'Transaction Date': 'date',
                'Amount': 'amount',
                'Description': 'description',
                'Payee': 'counterparty',
                'Reference': 'reference',
                'Category': 'category'
            },
            'credit_card': {
                'Date': 'date',
                'Posted Date': 'date',
                'Amount': 'amount',
                'Description': 'description',
                'Merchant': 'counterparty',
                'Reference Number': 'reference',
                'Category': 'category'
            }
        }
        
        mapping = column_mappings.get(source, {})
        df = df.rename(columns=mapping)
        
        # Ensure required columns exist
        required_columns = ['date', 'amount', 'description']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in file")
        
        return df

    def get_raw_transactions(
        self, 
        skip: int = 0, 
        limit: int = 100,
        source: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[TransactionRaw]:
        """Get raw transactions with filters"""
        query = self.db.query(TransactionRaw)
        
        if source:
            query = query.filter(TransactionRaw.source == source)
        if start_date:
            query = query.filter(TransactionRaw.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionRaw.transaction_date <= end_date)
        
        return query.offset(skip).limit(limit).all()

    def get_clean_transactions(
        self,
        skip: int = 0,
        limit: int = 100,
        classified_only: bool = False,
        reviewed_only: bool = False
    ) -> List[TransactionClean]:
        """Get cleaned transactions with filters"""
        query = self.db.query(TransactionClean)
        
        if classified_only:
            query = query.filter(TransactionClean.coa_id.isnot(None))
        if reviewed_only:
            query = query.filter(TransactionClean.is_reviewed == "true")
        
        return query.offset(skip).limit(limit).all()

    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics"""
        total_raw = self.db.query(func.count(TransactionRaw.id)).scalar()
        total_clean = self.db.query(func.count(TransactionClean.id)).scalar()
        classified_count = self.db.query(func.count(TransactionClean.id)).filter(
            TransactionClean.coa_id.isnot(None)
        ).scalar()
        reviewed_count = self.db.query(func.count(TransactionClean.id)).filter(
            TransactionClean.is_reviewed == "true"
        ).scalar()
        
        # Date range
        date_range_query = self.db.query(
            func.min(TransactionRaw.transaction_date).label('min_date'),
            func.max(TransactionRaw.transaction_date).label('max_date')
        ).first()
        
        return {
            'total_raw': total_raw,
            'total_clean': total_clean,
            'classified_count': classified_count,
            'reviewed_count': reviewed_count,
            'classification_rate': classified_count / total_clean if total_clean > 0 else 0,
            'review_rate': reviewed_count / total_clean if total_clean > 0 else 0,
            'date_range': {
                'min_date': date_range_query.min_date,
                'max_date': date_range_query.max_date
            }
        }

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction"""
        transaction = self.db.query(TransactionRaw).filter(
            TransactionRaw.id == transaction_id
        ).first()
        
        if transaction:
            # Also delete associated clean transaction
            clean_transaction = self.db.query(TransactionClean).filter(
                TransactionClean.raw_id == transaction_id
            ).first()
            if clean_transaction:
                self.db.delete(clean_transaction)
            
            self.db.delete(transaction)
            self.db.commit()
            return True
        
        return False