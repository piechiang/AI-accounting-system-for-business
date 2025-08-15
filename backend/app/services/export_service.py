from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
import csv
import os
import uuid
from io import StringIO

from app.models.transactions import TransactionClean
from app.models.accounts import ChartOfAccounts
from app.core.config import settings

class ExportService:
    def __init__(self, db: Session):
        self.db = db
        self.export_folder = "exports"
        os.makedirs(self.export_folder, exist_ok=True)

    async def export_to_quickbooks(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        export_type: str = "journal_entry",
        include_categories: bool = True,
        reviewed_only: bool = False
    ) -> Dict[str, Any]:
        """Export transactions to QuickBooks format"""
        
        # Get transactions
        transactions = self._get_transactions_for_export(
            start_date, end_date, reviewed_only
        )
        
        if not transactions:
            raise ValueError("No transactions found for export")
        
        # Generate export data based on type
        if export_type == "journal_entry":
            export_data = self._generate_qb_journal_entries(transactions)
            filename = f"QB_JournalEntries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "expense":
            export_data = self._generate_qb_expenses(transactions)
            filename = f"QB_Expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "bill":
            export_data = self._generate_qb_bills(transactions)
            filename = f"QB_Bills_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            raise ValueError(f"Unsupported QuickBooks export type: {export_type}")
        
        # Save to file
        file_path = os.path.join(self.export_folder, filename)
        self._save_csv_file(export_data, file_path)
        
        # Generate response
        file_id = str(uuid.uuid4())
        download_url = f"/api/v1/export/download/{file_id}"
        
        # Store file mapping (in production, use database)
        self._store_export_record(file_id, file_path, filename, len(transactions))
        
        return {
            'success': True,
            'message': f'Successfully exported {len(transactions)} transactions to QuickBooks format',
            'file_id': file_id,
            'filename': filename,
            'record_count': len(transactions),
            'file_size': os.path.getsize(file_path),
            'download_url': download_url,
            'expires_at': datetime.now().replace(hour=23, minute=59, second=59)  # End of day
        }

    async def export_to_xero(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        export_type: str = "journal_entry",
        include_tax_mapping: bool = True,
        reviewed_only: bool = False
    ) -> Dict[str, Any]:
        """Export transactions to Xero format"""
        
        transactions = self._get_transactions_for_export(
            start_date, end_date, reviewed_only
        )
        
        if not transactions:
            raise ValueError("No transactions found for export")
        
        # Generate export data based on type
        if export_type == "journal_entry":
            export_data = self._generate_xero_journal_entries(transactions, include_tax_mapping)
            filename = f"Xero_JournalEntries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "bank_transaction":
            export_data = self._generate_xero_bank_transactions(transactions)
            filename = f"Xero_BankTransactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            raise ValueError(f"Unsupported Xero export type: {export_type}")
        
        # Save to file
        file_path = os.path.join(self.export_folder, filename)
        self._save_csv_file(export_data, file_path)
        
        file_id = str(uuid.uuid4())
        download_url = f"/api/v1/export/download/{file_id}"
        
        self._store_export_record(file_id, file_path, filename, len(transactions))
        
        return {
            'success': True,
            'message': f'Successfully exported {len(transactions)} transactions to Xero format',
            'file_id': file_id,
            'filename': filename,
            'record_count': len(transactions),
            'file_size': os.path.getsize(file_path),
            'download_url': download_url,
            'expires_at': datetime.now().replace(hour=23, minute=59, second=59)
        }

    async def export_to_csv(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        export_type: str = "transactions",
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Export to generic CSV format"""
        
        if export_type == "transactions":
            data = self._export_transactions_csv(start_date, end_date, columns, filters)
            filename_prefix = "Transactions"
        elif export_type == "trial_balance":
            data = self._export_trial_balance_csv(start_date, end_date)
            filename_prefix = "TrialBalance"
        elif export_type == "general_ledger":
            data = self._export_general_ledger_csv(start_date, end_date, filters)
            filename_prefix = "GeneralLedger"
        else:
            raise ValueError(f"Unsupported CSV export type: {export_type}")
        
        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join(self.export_folder, filename)
        
        self._save_csv_file(data, file_path)
        
        file_id = str(uuid.uuid4())
        download_url = f"/api/v1/export/download/{file_id}"
        
        self._store_export_record(file_id, file_path, filename, len(data))
        
        return {
            'success': True,
            'message': f'Successfully exported {len(data)} records to CSV',
            'file_id': file_id,
            'filename': filename,
            'record_count': len(data),
            'file_size': os.path.getsize(file_path),
            'download_url': download_url,
            'expires_at': datetime.now().replace(hour=23, minute=59, second=59)
        }

    def _get_transactions_for_export(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        reviewed_only: bool = False
    ) -> List[TransactionClean]:
        """Get transactions for export with filters"""
        query = self.db.query(TransactionClean).join(
            ChartOfAccounts, TransactionClean.coa_id == ChartOfAccounts.id, isouter=True
        )
        
        if start_date:
            query = query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionClean.transaction_date <= end_date)
        if reviewed_only:
            query = query.filter(TransactionClean.is_reviewed == "true")
        
        return query.all()

    def _generate_qb_journal_entries(self, transactions: List[TransactionClean]) -> List[Dict[str, Any]]:
        """Generate QuickBooks journal entry format"""
        entries = []
        
        for txn in transactions:
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == txn.coa_id).first()
            
            # Debit entry (expense account)
            entries.append({
                'Date': txn.transaction_date.strftime('%m/%d/%Y'),
                'Account': coa.name if coa else 'Uncategorized Expense',
                'Debits': abs(txn.amount_base) if txn.amount_base < 0 else '',
                'Credits': abs(txn.amount_base) if txn.amount_base > 0 else '',
                'Memo': txn.description_normalized[:100] if txn.description_normalized else '',
                'Entity': txn.counterparty_normalized[:50] if txn.counterparty_normalized else ''
            })
            
            # Credit entry (bank/cash account)
            entries.append({
                'Date': txn.transaction_date.strftime('%m/%d/%Y'),
                'Account': 'Checking Account',  # Default bank account
                'Debits': abs(txn.amount_base) if txn.amount_base > 0 else '',
                'Credits': abs(txn.amount_base) if txn.amount_base < 0 else '',
                'Memo': txn.description_normalized[:100] if txn.description_normalized else '',
                'Entity': txn.counterparty_normalized[:50] if txn.counterparty_normalized else ''
            })
        
        return entries

    def _generate_qb_expenses(self, transactions: List[TransactionClean]) -> List[Dict[str, Any]]:
        """Generate QuickBooks expense format"""
        expenses = []
        
        for txn in transactions:
            if txn.amount_base >= 0:  # Only export expenses (negative amounts)
                continue
                
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == txn.coa_id).first()
            
            expenses.append({
                'Date': txn.transaction_date.strftime('%m/%d/%Y'),
                'Payee': txn.counterparty_normalized[:50] if txn.counterparty_normalized else 'Unknown',
                'Account': coa.name if coa else 'Uncategorized Expense',
                'Amount': abs(txn.amount_base),
                'Memo': txn.description_normalized[:200] if txn.description_normalized else '',
                'Payment method': 'Check'  # Default payment method
            })
        
        return expenses

    def _generate_qb_bills(self, transactions: List[TransactionClean]) -> List[Dict[str, Any]]:
        """Generate QuickBooks bill format"""
        bills = []
        
        # Group transactions by vendor
        vendor_transactions = {}
        for txn in transactions:
            if txn.amount_base >= 0:  # Only expenses
                continue
                
            vendor = txn.counterparty_normalized or 'Unknown Vendor'
            if vendor not in vendor_transactions:
                vendor_transactions[vendor] = []
            vendor_transactions[vendor].append(txn)
        
        # Create bills for each vendor
        for vendor, txns in vendor_transactions.items():
            total_amount = sum(abs(txn.amount_base) for txn in txns)
            latest_date = max(txn.transaction_date for txn in txns)
            
            bills.append({
                'Date': latest_date.strftime('%m/%d/%Y'),
                'Vendor': vendor[:50],
                'Amount': total_amount,
                'Memo': f"Combined bill for {len(txns)} transactions",
                'Terms': 'Net 30',
                'Due Date': (latest_date.replace(day=28) if latest_date.day > 28 else latest_date.replace(day=latest_date.day + 30)).strftime('%m/%d/%Y')
            })
        
        return bills

    def _generate_xero_journal_entries(self, transactions: List[TransactionClean], include_tax: bool = True) -> List[Dict[str, Any]]:
        """Generate Xero journal entry format"""
        entries = []
        
        for txn in transactions:
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == txn.coa_id).first()
            
            # Journal line item
            entries.append({
                'Date': txn.transaction_date.strftime('%d/%m/%Y'),  # Xero uses dd/mm/yyyy
                'Account': coa.code if coa else '6000',  # Default expense code
                'Description': txn.description_normalized[:200] if txn.description_normalized else '',
                'Reference': f"TXN-{txn.id}",
                'Debit': abs(txn.amount_base) if txn.amount_base < 0 else '',
                'Credit': abs(txn.amount_base) if txn.amount_base > 0 else '',
                'TaxType': 'GST' if include_tax else 'NONE',
                'Contact': txn.counterparty_normalized[:50] if txn.counterparty_normalized else ''
            })
        
        return entries

    def _generate_xero_bank_transactions(self, transactions: List[TransactionClean]) -> List[Dict[str, Any]]:
        """Generate Xero bank transaction format"""
        bank_txns = []
        
        for txn in transactions:
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == txn.coa_id).first()
            
            bank_txns.append({
                'Date': txn.transaction_date.strftime('%d/%m/%Y'),
                'Amount': txn.amount_base,
                'Payee': txn.counterparty_normalized[:50] if txn.counterparty_normalized else '',
                'Description': txn.description_normalized[:200] if txn.description_normalized else '',
                'Reference': f"TXN-{txn.id}",
                'Account': coa.code if coa else '6000'
            })
        
        return bank_txns

    def _export_transactions_csv(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        columns: Optional[List[str]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Export transactions to generic CSV format"""
        
        transactions = self._get_transactions_for_export(start_date, end_date)
        
        # Default columns if not specified
        if not columns:
            columns = [
                'id', 'transaction_date', 'amount_base', 'description_normalized',
                'counterparty_normalized', 'category_predicted', 'confidence_score'
            ]
        
        csv_data = []
        for txn in transactions:
            row = {}
            for col in columns:
                if hasattr(txn, col):
                    value = getattr(txn, col)
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        value = value.strftime('%Y-%m-%d')
                    row[col] = value
                else:
                    row[col] = ''
            
            # Apply additional filters if specified
            if filters:
                include_row = True
                for filter_key, filter_value in filters.items():
                    if filter_key in row and row[filter_key] != filter_value:
                        include_row = False
                        break
                
                if include_row:
                    csv_data.append(row)
            else:
                csv_data.append(row)
        
        return csv_data

    def _export_trial_balance_csv(
        self,
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> List[Dict[str, Any]]:
        """Export trial balance to CSV"""
        
        # Get account balances
        from sqlalchemy import func
        
        query = self.db.query(
            ChartOfAccounts.code,
            ChartOfAccounts.name,
            func.sum(TransactionClean.amount_base).label('balance')
        ).join(
            TransactionClean, TransactionClean.coa_id == ChartOfAccounts.id
        )
        
        if start_date:
            query = query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionClean.transaction_date <= end_date)
        
        balances = query.group_by(ChartOfAccounts.id).all()
        
        trial_balance = []
        for balance in balances:
            debit = abs(balance.balance) if balance.balance < 0 else 0
            credit = balance.balance if balance.balance > 0 else 0
            
            trial_balance.append({
                'Account Code': balance.code,
                'Account Name': balance.name,
                'Debit': debit,
                'Credit': credit,
                'Balance': balance.balance
            })
        
        return trial_balance

    def _export_general_ledger_csv(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Export general ledger to CSV"""
        
        transactions = self._get_transactions_for_export(start_date, end_date)
        
        ledger_entries = []
        for txn in transactions:
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == txn.coa_id).first()
            
            ledger_entries.append({
                'Date': txn.transaction_date.strftime('%Y-%m-%d'),
                'Account Code': coa.code if coa else '',
                'Account Name': coa.name if coa else 'Uncategorized',
                'Description': txn.description_normalized or '',
                'Reference': f"TXN-{txn.id}",
                'Debit': abs(txn.amount_base) if txn.amount_base < 0 else '',
                'Credit': abs(txn.amount_base) if txn.amount_base > 0 else '',
                'Balance': txn.amount_base
            })
        
        return ledger_entries

    def _save_csv_file(self, data: List[Dict[str, Any]], file_path: str):
        """Save data to CSV file"""
        if not data:
            raise ValueError("No data to export")
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def _store_export_record(self, file_id: str, file_path: str, filename: str, record_count: int):
        """Store export record (in production, use database)"""
        # For now, store in a simple dict (in production, use database)
        if not hasattr(self, '_export_records'):
            self._export_records = {}
        
        self._export_records[file_id] = {
            'file_path': file_path,
            'filename': filename,
            'record_count': record_count,
            'created_at': datetime.now()
        }

    def get_export_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get export file information"""
        if hasattr(self, '_export_records') and file_id in self._export_records:
            return self._export_records[file_id]
        return None

    def get_export_history(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get export history"""
        if not hasattr(self, '_export_records'):
            return []
        
        history = []
        for file_id, record in self._export_records.items():
            history.append({
                'id': file_id,
                'filename': record['filename'],
                'record_count': record['record_count'],
                'created_at': record['created_at'],
                'status': 'completed'
            })
        
        # Sort by creation date descending
        history.sort(key=lambda x: x['created_at'], reverse=True)
        
        return history[skip:skip+limit]

    def cleanup_old_exports(self, days_old: int = 30) -> int:
        """Cleanup old export files"""
        if not hasattr(self, '_export_records'):
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        files_to_remove = []
        for file_id, record in self._export_records.items():
            if record['created_at'] < cutoff_date:
                # Remove file
                if os.path.exists(record['file_path']):
                    os.remove(record['file_path'])
                files_to_remove.append(file_id)
                cleaned_count += 1
        
        # Remove from records
        for file_id in files_to_remove:
            del self._export_records[file_id]
        
        return cleaned_count