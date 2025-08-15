from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd

from app.models.transactions import TransactionClean
from app.models.accounts import ChartOfAccounts, Account
from app.models.reconciliation import Reconciliation

class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get dashboard summary with key metrics"""
        
        if not start_date:
            start_date = date.today().replace(day=1)  # Start of current month
        if not end_date:
            end_date = date.today()
        
        # Get transactions in period
        query = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        )
        
        transactions = query.all()
        
        if not transactions:
            return {
                'period_start': start_date,
                'period_end': end_date,
                'total_income': 0,
                'total_expenses': 0,
                'net_income': 0,
                'transaction_count': 0,
                'classified_percentage': 0,
                'reconciled_percentage': 0,
                'top_expense_category': None,
                'largest_transaction': None,
                'recent_activity_count': 0
            }
        
        # Calculate totals
        total_income = sum(txn.amount_base for txn in transactions if txn.amount_base > 0)
        total_expenses = sum(abs(txn.amount_base) for txn in transactions if txn.amount_base < 0)
        net_income = total_income - total_expenses
        
        # Classification metrics
        classified_count = sum(1 for txn in transactions if txn.coa_id is not None)
        classified_percentage = (classified_count / len(transactions)) * 100 if transactions else 0
        
        # Reconciliation metrics
        reconciled_count = self.db.query(func.count(Reconciliation.id)).filter(
            and_(
                Reconciliation.status == 'approved',
                Reconciliation.transaction_clean_id.in_([txn.id for txn in transactions])
            )
        ).scalar()
        reconciled_percentage = (reconciled_count / len(transactions)) * 100 if transactions else 0
        
        # Top expense category
        top_expense_category = self._get_top_expense_category(start_date, end_date)
        
        # Largest transaction
        largest_transaction = max(transactions, key=lambda x: abs(x.amount_base)) if transactions else None
        largest_txn_info = None
        if largest_transaction:
            largest_txn_info = {
                'id': largest_transaction.id,
                'amount': largest_transaction.amount_base,
                'date': largest_transaction.transaction_date,
                'description': largest_transaction.description_normalized,
                'counterparty': largest_transaction.counterparty_normalized
            }
        
        # Recent activity (last 7 days)
        recent_date = date.today() - timedelta(days=7)
        recent_activity_count = self.db.query(func.count(TransactionClean.id)).filter(
            TransactionClean.transaction_date >= recent_date
        ).scalar()
        
        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'transaction_count': len(transactions),
            'classified_percentage': classified_percentage,
            'reconciled_percentage': reconciled_percentage,
            'top_expense_category': top_expense_category,
            'largest_transaction': largest_txn_info,
            'recent_activity_count': recent_activity_count
        }

    def get_expense_categories(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top expense categories"""
        
        query = self.db.query(
            ChartOfAccounts.name,
            ChartOfAccounts.code,
            func.sum(func.abs(TransactionClean.amount_base)).label('total_amount'),
            func.count(TransactionClean.id).label('transaction_count')
        ).join(
            TransactionClean, TransactionClean.coa_id == ChartOfAccounts.id
        ).filter(
            TransactionClean.amount_base < 0  # Only expenses
        )
        
        if start_date:
            query = query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionClean.transaction_date <= end_date)
        
        results = query.group_by(
            ChartOfAccounts.id
        ).order_by(
            desc('total_amount')
        ).limit(limit).all()
        
        # Calculate total for percentage
        total_expenses = sum(result.total_amount for result in results)
        
        categories = []
        for result in results:
            percentage = (result.total_amount / total_expenses * 100) if total_expenses > 0 else 0
            
            categories.append({
                'category_name': result.name,
                'category_code': result.code,
                'total_amount': result.total_amount,
                'transaction_count': result.transaction_count,
                'percentage_of_total': percentage,
                'trend': self._calculate_category_trend(result.name, start_date, end_date)
            })
        
        return categories

    def get_revenue_analysis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: str = "month"
    ) -> List[Dict[str, Any]]:
        """Get revenue analysis over time"""
        
        if not start_date:
            start_date = date.today() - timedelta(days=365)  # Last year
        if not end_date:
            end_date = date.today()
        
        # Get revenue transactions
        query = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.amount_base > 0,
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        )
        
        transactions = query.all()
        
        if not transactions:
            return []
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'date': txn.transaction_date,
            'amount': txn.amount_base
        } for txn in transactions])
        
        # Group by specified period
        if group_by == "day":
            df['period'] = df['date'].dt.date
            period_format = lambda x: x.strftime('%Y-%m-%d')
        elif group_by == "week":
            df['period'] = df['date'].dt.to_period('W')
            period_format = lambda x: f"Week of {x.start_time.strftime('%Y-%m-%d')}"
        elif group_by == "month":
            df['period'] = df['date'].dt.to_period('M')
            period_format = lambda x: x.strftime('%Y-%m')
        elif group_by == "quarter":
            df['period'] = df['date'].dt.to_period('Q')
            period_format = lambda x: f"Q{x.quarter} {x.year}"
        else:
            raise ValueError(f"Unsupported group_by value: {group_by}")
        
        # Aggregate by period
        period_revenue = df.groupby('period').agg({
            'amount': ['sum', 'count']
        }).reset_index()
        
        period_revenue.columns = ['period', 'revenue', 'transaction_count']
        period_revenue = period_revenue.sort_values('period')
        
        # Calculate growth rates
        period_revenue['growth_rate'] = period_revenue['revenue'].pct_change() * 100
        
        # Convert to response format
        analysis = []
        for _, row in period_revenue.iterrows():
            analysis.append({
                'period': period_format(row['period']),
                'revenue': row['revenue'],
                'growth_rate': row['growth_rate'] if not pd.isna(row['growth_rate']) else None,
                'transaction_count': int(row['transaction_count'])
            })
        
        return analysis

    def get_cash_flow_analysis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: str = "month"
    ) -> List[Dict[str, Any]]:
        """Get cash flow analysis"""
        
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()
        
        # Get all transactions
        query = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        )
        
        transactions = query.all()
        
        if not transactions:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': txn.transaction_date,
            'amount': txn.amount_base
        } for txn in transactions])
        
        # Group by period
        if group_by == "month":
            df['period'] = df['date'].dt.to_period('M')
            period_format = lambda x: x.strftime('%Y-%m')
        elif group_by == "quarter":
            df['period'] = df['date'].dt.to_period('Q')  
            period_format = lambda x: f"Q{x.quarter} {x.year}"
        elif group_by == "week":
            df['period'] = df['date'].dt.to_period('W')
            period_format = lambda x: f"Week of {x.start_time.strftime('%Y-%m-%d')}"
        else:
            df['period'] = df['date'].dt.date
            period_format = lambda x: x.strftime('%Y-%m-%d')
        
        # Separate cash in and cash out
        df['cash_in'] = df['amount'].where(df['amount'] > 0, 0)
        df['cash_out'] = df['amount'].where(df['amount'] < 0, 0).abs()
        
        # Aggregate by period
        period_cash_flow = df.groupby('period').agg({
            'cash_in': 'sum',
            'cash_out': 'sum'
        }).reset_index()
        
        period_cash_flow['net_cash_flow'] = period_cash_flow['cash_in'] - period_cash_flow['cash_out']
        period_cash_flow = period_cash_flow.sort_values('period')
        
        # Convert to response format
        cash_flow = []
        for _, row in period_cash_flow.iterrows():
            cash_flow.append({
                'period': period_format(row['period']),
                'cash_in': row['cash_in'],
                'cash_out': row['cash_out'],
                'net_cash_flow': row['net_cash_flow']
            })
        
        return cash_flow

    def get_anomalies(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        anomaly_types: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get anomalous transactions"""
        
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        anomalies = []
        
        # Get transactions in period
        query = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        )
        
        transactions = query.all()
        amounts = [abs(txn.amount_base) for txn in transactions]
        
        if not amounts:
            return []
        
        # Calculate statistics for amount-based anomalies
        import numpy as np
        q75, q25 = np.percentile(amounts, [75, 25])
        iqr = q75 - q25
        upper_bound = q75 + 1.5 * iqr
        lower_bound = q25 - 1.5 * iqr
        
        requested_types = anomaly_types.split(',') if anomaly_types else ['amount', 'frequency', 'new_vendor']
        
        for txn in transactions:
            txn_amount = abs(txn.amount_base)
            
            # Amount-based anomalies
            if 'amount' in requested_types:
                if txn_amount > upper_bound:
                    severity = 'high' if txn_amount > upper_bound * 2 else 'medium'
                    anomalies.append({
                        'transaction_id': txn.id,
                        'anomaly_type': 'amount',
                        'description': txn.description_normalized or '',
                        'amount': txn.amount_base,
                        'date': txn.transaction_date.date(),
                        'severity': severity,
                        'reason': f'Amount ${txn_amount:,.2f} is unusually high (above ${upper_bound:,.2f})'
                    })
            
            # New vendor anomalies
            if 'new_vendor' in requested_types and txn.counterparty_normalized:
                # Check if this vendor appeared in the last 90 days
                vendor_history = self.db.query(TransactionClean).filter(
                    and_(
                        TransactionClean.counterparty_normalized == txn.counterparty_normalized,
                        TransactionClean.transaction_date < txn.transaction_date - timedelta(days=90),
                        TransactionClean.id != txn.id
                    )
                ).first()
                
                if not vendor_history:
                    anomalies.append({
                        'transaction_id': txn.id,
                        'anomaly_type': 'new_vendor',
                        'description': txn.description_normalized or '',
                        'amount': txn.amount_base,
                        'date': txn.transaction_date.date(),
                        'severity': 'low',
                        'reason': f'First transaction with vendor: {txn.counterparty_normalized}'
                    })
        
        # Frequency-based anomalies (transactions on unusual days/times)
        if 'frequency' in requested_types:
            weekend_transactions = [
                txn for txn in transactions 
                if txn.transaction_date.weekday() >= 5  # Saturday = 5, Sunday = 6
            ]
            
            for txn in weekend_transactions:
                anomalies.append({
                    'transaction_id': txn.id,
                    'anomaly_type': 'frequency',
                    'description': txn.description_normalized or '',
                    'amount': txn.amount_base,
                    'date': txn.transaction_date.date(),
                    'severity': 'low',
                    'reason': 'Transaction occurred on weekend'
                })
        
        # Sort by severity and amount
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        anomalies.sort(key=lambda x: (severity_order[x['severity']], abs(x['amount'])), reverse=True)
        
        return anomalies[:50]  # Return top 50 anomalies

    def get_top_vendors(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top vendors by spending"""
        
        query = self.db.query(
            TransactionClean.counterparty_normalized,
            func.sum(func.abs(TransactionClean.amount_base)).label('total_spent'),
            func.count(TransactionClean.id).label('transaction_count'),
            func.avg(func.abs(TransactionClean.amount_base)).label('average_amount'),
            func.max(TransactionClean.transaction_date).label('last_transaction_date')
        ).filter(
            and_(
                TransactionClean.amount_base < 0,  # Only expenses
                TransactionClean.counterparty_normalized.isnot(None)
            )
        )
        
        if start_date:
            query = query.filter(TransactionClean.transaction_date >= start_date)
        if end_date:
            query = query.filter(TransactionClean.transaction_date <= end_date)
        
        results = query.group_by(
            TransactionClean.counterparty_normalized
        ).order_by(
            desc('total_spent')
        ).limit(limit).all()
        
        vendors = []
        for result in results:
            # Get most common category for this vendor
            category_query = self.db.query(
                ChartOfAccounts.name
            ).join(
                TransactionClean, TransactionClean.coa_id == ChartOfAccounts.id
            ).filter(
                TransactionClean.counterparty_normalized == result.counterparty_normalized
            ).group_by(
                ChartOfAccounts.name
            ).order_by(
                desc(func.count(TransactionClean.id))
            ).first()
            
            vendors.append({
                'vendor_name': result.counterparty_normalized,
                'total_spent': result.total_spent,
                'transaction_count': result.transaction_count,
                'average_amount': result.average_amount,
                'last_transaction_date': result.last_transaction_date.date(),
                'category': category_query.name if category_query else None
            })
        
        return vendors

    def get_spending_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get spending trends analysis"""
        
        if not start_date:
            start_date = date.today() - timedelta(days=180)  # Last 6 months
        if not end_date:
            end_date = date.today()
        
        # Build query
        query = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.amount_base < 0,  # Only expenses
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        )
        
        if category:
            query = query.join(ChartOfAccounts).filter(
                ChartOfAccounts.name.ilike(f'%{category}%')
            )
        
        transactions = query.all()
        
        if not transactions:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': txn.transaction_date,
            'amount': abs(txn.amount_base),
            'category': self._get_transaction_category(txn)
        } for txn in transactions])
        
        # Group by month and category
        df['month'] = df['date'].dt.to_period('M')
        
        if category:
            # Single category trend
            monthly_spending = df.groupby('month')['amount'].sum().reset_index()
            trends = []
            
            for i, row in monthly_spending.iterrows():
                if i > 0:
                    prev_amount = monthly_spending.iloc[i-1]['amount']
                    change_pct = ((row['amount'] - prev_amount) / prev_amount) * 100
                    
                    if change_pct > 10:
                        trend_direction = 'increasing'
                    elif change_pct < -10:
                        trend_direction = 'decreasing'
                    else:
                        trend_direction = 'stable'
                    
                    trends.append({
                        'category': category,
                        'period': row['month'].strftime('%Y-%m'),
                        'amount': row['amount'],
                        'trend_direction': trend_direction,
                        'trend_strength': abs(change_pct)
                    })
        else:
            # Multi-category trends
            category_trends = df.groupby(['month', 'category'])['amount'].sum().reset_index()
            trends = []
            
            for cat in df['category'].unique():
                cat_data = category_trends[category_trends['category'] == cat].sort_values('month')
                
                if len(cat_data) > 1:
                    latest_amount = cat_data.iloc[-1]['amount']
                    prev_amount = cat_data.iloc[-2]['amount']
                    change_pct = ((latest_amount - prev_amount) / prev_amount) * 100
                    
                    if change_pct > 15:
                        trend_direction = 'increasing'
                        trend_strength = min(100, abs(change_pct))
                    elif change_pct < -15:
                        trend_direction = 'decreasing'
                        trend_strength = min(100, abs(change_pct))
                    else:
                        trend_direction = 'stable'
                        trend_strength = abs(change_pct)
                    
                    trends.append({
                        'category': cat,
                        'period': cat_data.iloc[-1]['month'].strftime('%Y-%m'),
                        'amount': latest_amount,
                        'trend_direction': trend_direction,
                        'trend_strength': trend_strength
                    })
        
        return sorted(trends, key=lambda x: x['trend_strength'], reverse=True)

    def get_kpis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        compare_previous_period: bool = True
    ) -> List[Dict[str, Any]]:
        """Get key performance indicators"""
        
        if not start_date:
            start_date = date.today().replace(day=1)  # Start of current month
        if not end_date:
            end_date = date.today()
        
        period_days = (end_date - start_date).days + 1
        
        # Get current period transactions
        current_txns = self.db.query(TransactionClean).filter(
            and_(
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        ).all()
        
        kpis = []
        
        # Revenue KPI
        current_revenue = sum(txn.amount_base for txn in current_txns if txn.amount_base > 0)
        
        # Expenses KPI
        current_expenses = sum(abs(txn.amount_base) for txn in current_txns if txn.amount_base < 0)
        
        # Net Income KPI
        current_net_income = current_revenue - current_expenses
        
        # Transaction Volume KPI
        current_txn_count = len(current_txns)
        
        # Average Transaction Size KPI
        current_avg_txn = (current_revenue + current_expenses) / current_txn_count if current_txn_count > 0 else 0
        
        if compare_previous_period:
            # Get previous period data
            prev_start = start_date - timedelta(days=period_days)
            prev_end = start_date - timedelta(days=1)
            
            prev_txns = self.db.query(TransactionClean).filter(
                and_(
                    TransactionClean.transaction_date >= prev_start,
                    TransactionClean.transaction_date <= prev_end
                )
            ).all()
            
            prev_revenue = sum(txn.amount_base for txn in prev_txns if txn.amount_base > 0)
            prev_expenses = sum(abs(txn.amount_base) for txn in prev_txns if txn.amount_base < 0)
            prev_net_income = prev_revenue - prev_expenses
            prev_txn_count = len(prev_txns)
            prev_avg_txn = (prev_revenue + prev_expenses) / prev_txn_count if prev_txn_count > 0 else 0
            
            # Calculate changes
            revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
            expenses_change = ((current_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
            net_income_change = ((current_net_income - prev_net_income) / abs(prev_net_income) * 100) if prev_net_income != 0 else 0
            txn_count_change = ((current_txn_count - prev_txn_count) / prev_txn_count * 100) if prev_txn_count > 0 else 0
            avg_txn_change = ((current_avg_txn - prev_avg_txn) / prev_avg_txn * 100) if prev_avg_txn > 0 else 0
        else:
            # No comparison data
            revenue_change = expenses_change = net_income_change = txn_count_change = avg_txn_change = None
            prev_revenue = prev_expenses = prev_net_income = prev_txn_count = prev_avg_txn = None
        
        # Build KPI list
        kpis = [
            {
                'kpi_name': 'Total Revenue',
                'current_value': current_revenue,
                'previous_value': prev_revenue,
                'change_percentage': revenue_change,
                'trend': 'up' if revenue_change and revenue_change > 0 else 'down' if revenue_change and revenue_change < 0 else 'stable',
                'benchmark': None
            },
            {
                'kpi_name': 'Total Expenses', 
                'current_value': current_expenses,
                'previous_value': prev_expenses,
                'change_percentage': expenses_change,
                'trend': 'up' if expenses_change and expenses_change > 0 else 'down' if expenses_change and expenses_change < 0 else 'stable',
                'benchmark': None
            },
            {
                'kpi_name': 'Net Income',
                'current_value': current_net_income,
                'previous_value': prev_net_income,
                'change_percentage': net_income_change,
                'trend': 'up' if net_income_change and net_income_change > 0 else 'down' if net_income_change and net_income_change < 0 else 'stable',
                'benchmark': None
            },
            {
                'kpi_name': 'Transaction Volume',
                'current_value': current_txn_count,
                'previous_value': prev_txn_count,
                'change_percentage': txn_count_change,
                'trend': 'up' if txn_count_change and txn_count_change > 0 else 'down' if txn_count_change and txn_count_change < 0 else 'stable',
                'benchmark': None
            },
            {
                'kpi_name': 'Average Transaction Size',
                'current_value': current_avg_txn,
                'previous_value': prev_avg_txn,
                'change_percentage': avg_txn_change,
                'trend': 'up' if avg_txn_change and avg_txn_change > 0 else 'down' if avg_txn_change and avg_txn_change < 0 else 'stable',
                'benchmark': None
            }
        ]
        
        return kpis

    # Helper methods
    def _get_top_expense_category(self, start_date: date, end_date: date) -> Optional[str]:
        """Get the top expense category for the period"""
        result = self.db.query(
            ChartOfAccounts.name,
            func.sum(func.abs(TransactionClean.amount_base)).label('total')
        ).join(
            TransactionClean, TransactionClean.coa_id == ChartOfAccounts.id
        ).filter(
            and_(
                TransactionClean.amount_base < 0,
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date <= end_date
            )
        ).group_by(ChartOfAccounts.id).order_by(desc('total')).first()
        
        return result.name if result else None

    def _calculate_category_trend(self, category_name: str, start_date: Optional[date], end_date: Optional[date]) -> str:
        """Calculate trend for a category (simplified)"""
        if not start_date or not end_date:
            return 'stable'
        
        # Compare first half vs second half of period
        period_days = (end_date - start_date).days
        mid_date = start_date + timedelta(days=period_days // 2)
        
        first_half = self.db.query(func.sum(func.abs(TransactionClean.amount_base))).join(
            ChartOfAccounts
        ).filter(
            and_(
                ChartOfAccounts.name == category_name,
                TransactionClean.transaction_date >= start_date,
                TransactionClean.transaction_date < mid_date,
                TransactionClean.amount_base < 0
            )
        ).scalar() or 0
        
        second_half = self.db.query(func.sum(func.abs(TransactionClean.amount_base))).join(
            ChartOfAccounts
        ).filter(
            and_(
                ChartOfAccounts.name == category_name,
                TransactionClean.transaction_date >= mid_date,
                TransactionClean.transaction_date <= end_date,
                TransactionClean.amount_base < 0
            )
        ).scalar() or 0
        
        if first_half > 0:
            change_pct = ((second_half - first_half) / first_half) * 100
            if change_pct > 10:
                return 'up'
            elif change_pct < -10:
                return 'down'
        
        return 'stable'

    def _get_transaction_category(self, transaction: TransactionClean) -> str:
        """Get category name for transaction"""
        if transaction.coa_id:
            coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == transaction.coa_id).first()
            return coa.name if coa else 'Uncategorized'
        return 'Uncategorized'