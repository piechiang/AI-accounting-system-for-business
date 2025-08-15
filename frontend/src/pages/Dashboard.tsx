import React, { useState, useEffect } from 'react';

interface DashboardMetrics {
  total_transactions: number;
  total_amount: number;
  classified_transactions: number;
  reconciled_transactions: number;
  classification_accuracy: number;
  reconciliation_rate: number;
  top_categories: Array<{
    category: string;
    amount: number;
    count: number;
  }>;
  recent_transactions: Array<{
    id: number;
    date: string;
    description: string;
    amount: number;
    category: string;
  }>;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardMetrics();
  }, []);

  const fetchDashboardMetrics = async () => {
    try {
      setLoading(true);
      // Mock data for now - in production this would fetch from the API
      const mockData: DashboardMetrics = {
        total_transactions: 29,
        total_amount: 15432.50,
        classified_transactions: 27,
        reconciled_transactions: 25,
        classification_accuracy: 0.95,
        reconciliation_rate: 0.86,
        top_categories: [
          { category: 'Office Supplies', amount: 3245.67, count: 8 },
          { category: 'Software Expenses', amount: 2156.99, count: 5 },
          { category: 'Travel Expenses', amount: 1890.45, count: 4 },
          { category: 'Meals & Entertainment', amount: 987.33, count: 6 },
          { category: 'Vehicle Expenses', amount: 543.21, count: 3 },
        ],
        recent_transactions: [
          { id: 1, date: '2024-01-15', description: 'Amazon.com Purchase', amount: -89.99, category: 'Office Supplies' },
          { id: 2, date: '2024-01-14', description: 'Microsoft 365', amount: -15.99, category: 'Software' },
          { id: 3, date: '2024-01-12', description: 'Client Payment', amount: 2500.00, category: 'Revenue' },
          { id: 4, date: '2024-01-10', description: 'Uber Ride', amount: -45.67, category: 'Travel' },
          { id: 5, date: '2024-01-08', description: 'Starbucks', amount: -12.45, category: 'Meals' },
        ]
      };
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      setMetrics(mockData);
    } catch (error) {
      console.error('Failed to fetch dashboard metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">Failed to load dashboard data</p>
        <button 
          onClick={fetchDashboardMetrics}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Financial Dashboard</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Transactions"
          value={metrics.total_transactions.toString()}
          subtitle="This month"
          icon="📊"
          color="blue"
        />
        <MetricCard
          title="Total Amount"
          value={`$${metrics.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle="Net cash flow"
          icon="💰"
          color="green"
        />
        <MetricCard
          title="Classification Rate"
          value={`${(metrics.classification_accuracy * 100).toFixed(1)}%`}
          subtitle={`${metrics.classified_transactions}/${metrics.total_transactions} classified`}
          icon="🤖"
          color="purple"
        />
        <MetricCard
          title="Reconciliation Rate"
          value={`${(metrics.reconciliation_rate * 100).toFixed(1)}%`}
          subtitle={`${metrics.reconciled_transactions}/${metrics.total_transactions} matched`}
          icon="🔄"
          color="indigo"
        />
      </div>

      {/* Charts and Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Categories */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Top Expense Categories</h2>
          <div className="space-y-3">
            {metrics.top_categories.map((category, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{category.category}</span>
                    <span className="text-gray-500">{category.count} transactions</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div 
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ 
                        width: `${(category.amount / metrics.top_categories[0].amount) * 100}%` 
                      }}
                    ></div>
                  </div>
                </div>
                <div className="ml-4 text-right">
                  <div className="font-semibold">${category.amount.toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Transactions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Transactions</h2>
          <div className="space-y-3">
            {metrics.recent_transactions.map((transaction) => (
              <div key={transaction.id} className="flex items-center justify-between border-b pb-2">
                <div className="flex-1">
                  <div className="font-medium text-sm">{transaction.description}</div>
                  <div className="text-xs text-gray-500">{transaction.date} • {transaction.category}</div>
                </div>
                <div className={`font-semibold ${transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {transaction.amount >= 0 ? '+' : ''}${Math.abs(transaction.amount).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-center">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View All Transactions →
            </button>
          </div>
        </div>
      </div>

      {/* Action Items */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-yellow-800 mb-2">Action Items</h3>
        <div className="space-y-2">
          <div className="flex items-center text-yellow-700">
            <span className="mr-2">⚠️</span>
            <span>{metrics.total_transactions - metrics.classified_transactions} transactions need classification</span>
          </div>
          <div className="flex items-center text-yellow-700">
            <span className="mr-2">🔍</span>
            <span>{metrics.total_transactions - metrics.reconciled_transactions} transactions need reconciliation</span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'indigo';
}

function MetricCard({ title, value, subtitle, icon, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    indigo: 'bg-indigo-500',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`${colorClasses[color]} rounded-lg p-3`}>
          <span className="text-white text-2xl">{icon}</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}