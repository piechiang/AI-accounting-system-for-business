import React, { useState, useEffect } from 'react';
import { toast } from '../components/ui/Toaster';

interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  counterparty: string;
  category: string;
  confidence: number;
  status: 'classified' | 'pending' | 'reviewed';
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'classified'>('all');

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      // Mock data - in production this would fetch from the API
      const mockTransactions: Transaction[] = [
        {
          id: 1,
          date: '2024-01-15',
          description: 'Amazon.com Purchase',
          amount: -89.99,
          counterparty: 'Amazon.com',
          category: 'Office Supplies',
          confidence: 0.95,
          status: 'classified'
        },
        {
          id: 2,
          date: '2024-01-14',
          description: 'Microsoft 365 Subscription',
          amount: -15.99,
          counterparty: 'Microsoft',
          category: 'Software Expenses',
          confidence: 0.98,
          status: 'classified'
        },
        {
          id: 3,
          date: '2024-01-12',
          description: 'Client Payment - XYZ Corp',
          amount: 2500.00,
          counterparty: 'XYZ Corp',
          category: 'Revenue',
          confidence: 0.99,
          status: 'reviewed'
        },
        {
          id: 4,
          date: '2024-01-10',
          description: 'Uber Ride to Airport',
          amount: -45.67,
          counterparty: 'Uber',
          category: '',
          confidence: 0,
          status: 'pending'
        },
        {
          id: 5,
          date: '2024-01-08',
          description: 'Starbucks Coffee #1234',
          amount: -12.45,
          counterparty: 'Starbucks',
          category: 'Meals & Entertainment',
          confidence: 0.87,
          status: 'classified'
        },
      ];

      await new Promise(resolve => setTimeout(resolve, 800));
      setTransactions(mockTransactions);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
      toast.error('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file');
      return;
    }

    setUploading(true);
    try {
      // Mock upload - in production this would upload to the API
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.success(`Successfully uploaded ${file.name}`);
      fetchTransactions(); // Refresh transactions
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const handleClassifyAll = async () => {
    const pendingTransactions = transactions.filter(t => t.status === 'pending');
    if (pendingTransactions.length === 0) {
      toast.info('No pending transactions to classify');
      return;
    }

    setLoading(true);
    try {
      // Mock classification - in production this would call the AI classification API
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setTransactions(prev => prev.map(t => 
        t.status === 'pending' 
          ? { ...t, category: 'Travel Expenses', confidence: 0.89, status: 'classified' as const }
          : t
      ));
      
      toast.success(`Classified ${pendingTransactions.length} transactions`);
    } catch (error) {
      toast.error('Classification failed');
    } finally {
      setLoading(false);
    }
  };

  const filteredTransactions = transactions.filter(transaction => {
    switch (filter) {
      case 'pending':
        return transaction.status === 'pending';
      case 'classified':
        return transaction.status === 'classified' || transaction.status === 'reviewed';
      default:
        return true;
    }
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Transaction Management</h1>
        <div className="flex space-x-3">
          <button
            onClick={handleClassifyAll}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <span className="mr-2">🤖</span>
            {loading ? 'Classifying...' : 'Classify All'}
          </button>
        </div>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Upload Transactions</h2>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input
            type="file"
            id="file-upload"
            accept=".csv"
            onChange={handleFileUpload}
            className="hidden"
            disabled={uploading}
          />
          <label
            htmlFor="file-upload"
            className={`cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <div className="space-y-2">
              <div className="text-4xl">📁</div>
              <div className="text-lg font-medium">
                {uploading ? 'Uploading...' : 'Upload CSV File'}
              </div>
              <div className="text-sm text-gray-500">
                Supported formats: Bank statements, Credit card exports, General ledger
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Filter and Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <div className="flex space-x-2">
            {(['all', 'pending', 'classified'] as const).map((filterType) => (
              <button
                key={filterType}
                onClick={() => setFilter(filterType)}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  filter === filterType
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filterType.charAt(0).toUpperCase() + filterType.slice(1)}
                {filterType === 'pending' && (
                  <span className="ml-1 bg-red-100 text-red-800 text-xs px-2 py-1 rounded-full">
                    {transactions.filter(t => t.status === 'pending').length}
                  </span>
                )}
              </button>
            ))}
          </div>
          
          <div className="text-sm text-gray-500">
            Showing {filteredTransactions.length} of {transactions.length} transactions
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Counterparty
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                      <span className="ml-2">Loading transactions...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No transactions found
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {transaction.date}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {transaction.description}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {transaction.counterparty}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <span className={transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {transaction.amount >= 0 ? '+' : ''}${Math.abs(transaction.amount).toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {transaction.category || (
                        <span className="text-gray-400 italic">Unclassified</span>
                      )}
                      {transaction.confidence > 0 && (
                        <div className="text-xs text-gray-500 mt-1">
                          Confidence: {(transaction.confidence * 100).toFixed(1)}%
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        transaction.status === 'reviewed' 
                          ? 'bg-green-100 text-green-800'
                          : transaction.status === 'classified'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {transaction.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}