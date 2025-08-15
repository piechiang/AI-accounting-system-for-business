import React, { useState, useEffect } from 'react';
import { toast } from '../components/ui/Toaster';

interface ReconciliationMatch {
  id: number;
  transaction: {
    id: number;
    date: string;
    description: string;
    amount: number;
  };
  ledger_entry: {
    id: number;
    date: string;
    memo: string;
    amount: number;
  };
  match_type: 'exact' | 'windowed' | 'fuzzy';
  match_score: number;
  status: 'pending' | 'approved' | 'rejected';
  amount_difference: number;
  date_difference_days: number;
}

export default function Reconciliation() {
  const [matches, setMatches] = useState<ReconciliationMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    total_transactions: 0,
    matched_count: 0,
    match_rate: 0,
    auto_match_rate: 0
  });

  useEffect(() => {
    fetchReconciliationData();
  }, []);

  const fetchReconciliationData = async () => {
    setLoading(true);
    try {
      // Mock data
      const mockMatches: ReconciliationMatch[] = [
        {
          id: 1,
          transaction: {
            id: 101,
            date: '2024-01-15',
            description: 'Amazon.com Purchase',
            amount: -89.99
          },
          ledger_entry: {
            id: 201,
            date: '2024-01-15',
            memo: 'Office supplies - Amazon',
            amount: -89.99
          },
          match_type: 'exact',
          match_score: 1.0,
          status: 'approved',
          amount_difference: 0,
          date_difference_days: 0
        },
        {
          id: 2,
          transaction: {
            id: 102,
            date: '2024-01-14',
            description: 'Microsoft 365 Subscription',
            amount: -15.99
          },
          ledger_entry: {
            id: 202,
            date: '2024-01-15',
            memo: 'Software license - Microsoft',
            amount: -15.99
          },
          match_type: 'windowed',
          match_score: 0.9,
          status: 'pending',
          amount_difference: 0,
          date_difference_days: 1
        },
        {
          id: 3,
          transaction: {
            id: 103,
            date: '2024-01-12',
            description: 'Client Payment - XYZ Corp',
            amount: 2500.00
          },
          ledger_entry: {
            id: 203,
            date: '2024-01-12',
            memo: 'Invoice payment XYZ',
            amount: 2500.00
          },
          match_type: 'fuzzy',
          match_score: 0.87,
          status: 'pending',
          amount_difference: 0,
          date_difference_days: 0
        }
      ];

      const mockStats = {
        total_transactions: 29,
        matched_count: 25,
        match_rate: 0.86,
        auto_match_rate: 0.72
      };

      await new Promise(resolve => setTimeout(resolve, 800));
      setMatches(mockMatches);
      setStats(mockStats);
    } catch (error) {
      toast.error('Failed to load reconciliation data');
    } finally {
      setLoading(false);
    }
  };

  const handleAutoReconcile = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simulate finding new matches
      const newMatch: ReconciliationMatch = {
        id: 4,
        transaction: {
          id: 104,
          date: '2024-01-10',
          description: 'Uber Ride to Airport',
          amount: -45.67
        },
        ledger_entry: {
          id: 204,
          date: '2024-01-10',
          memo: 'Transportation expense',
          amount: -45.67
        },
        match_type: 'exact',
        match_score: 1.0,
        status: 'pending',
        amount_difference: 0,
        date_difference_days: 0
      };

      setMatches(prev => [...prev, newMatch]);
      setStats(prev => ({
        ...prev,
        matched_count: prev.matched_count + 1,
        match_rate: (prev.matched_count + 1) / prev.total_transactions
      }));
      
      toast.success('Auto-reconciliation found 1 new match');
    } catch (error) {
      toast.error('Auto-reconciliation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveMatch = async (matchId: number) => {
    try {
      setMatches(prev => 
        prev.map(match => 
          match.id === matchId 
            ? { ...match, status: 'approved' as const }
            : match
        )
      );
      toast.success('Match approved');
    } catch (error) {
      toast.error('Failed to approve match');
    }
  };

  const handleRejectMatch = async (matchId: number) => {
    try {
      setMatches(prev => 
        prev.map(match => 
          match.id === matchId 
            ? { ...match, status: 'rejected' as const }
            : match
        )
      );
      toast.success('Match rejected');
    } catch (error) {
      toast.error('Failed to reject match');
    }
  };

  const getMatchTypeColor = (type: string) => {
    switch (type) {
      case 'exact': return 'bg-green-100 text-green-800';
      case 'windowed': return 'bg-blue-100 text-blue-800';
      case 'fuzzy': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Bank Reconciliation</h1>
        <button
          onClick={handleAutoReconcile}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <span className="mr-2">🔄</span>
          {loading ? 'Reconciling...' : 'Auto Reconcile'}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-blue-500 rounded-lg p-3">
              <span className="text-white text-2xl">💳</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Transactions</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total_transactions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-green-500 rounded-lg p-3">
              <span className="text-white text-2xl">✅</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Matched</p>
              <p className="text-2xl font-bold text-gray-900">{stats.matched_count}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-purple-500 rounded-lg p-3">
              <span className="text-white text-2xl">📊</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Match Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {(stats.match_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-indigo-500 rounded-lg p-3">
              <span className="text-white text-2xl">🤖</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Auto Match Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {(stats.auto_match_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Reconciliation Matches */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Reconciliation Matches</h2>
        </div>
        
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-2">Loading matches...</span>
            </div>
          ) : matches.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-4">🔍</div>
              <div className="text-lg font-medium mb-2">No matches found</div>
              <div>Run auto-reconciliation to find potential matches.</div>
            </div>
          ) : (
            <div className="space-y-4">
              {matches.map((match) => (
                <div key={match.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getMatchTypeColor(match.match_type)}`}>
                        {match.match_type.toUpperCase()}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(match.status)}`}>
                        {match.status.toUpperCase()}
                      </span>
                      <div className="flex items-center text-sm text-gray-500">
                        <span>Score:</span>
                        <div className="ml-2 flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${match.match_score * 100}%` }}
                            ></div>
                          </div>
                          <span className="ml-2 font-medium">
                            {(match.match_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Bank Transaction */}
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h4 className="font-medium text-blue-900 mb-2">Bank Transaction</h4>
                      <div className="space-y-1 text-sm">
                        <div><span className="font-medium">Date:</span> {match.transaction.date}</div>
                        <div><span className="font-medium">Description:</span> {match.transaction.description}</div>
                        <div><span className="font-medium">Amount:</span> 
                          <span className={match.transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${Math.abs(match.transaction.amount).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Ledger Entry */}
                    <div className="bg-green-50 rounded-lg p-4">
                      <h4 className="font-medium text-green-900 mb-2">Ledger Entry</h4>
                      <div className="space-y-1 text-sm">
                        <div><span className="font-medium">Date:</span> {match.ledger_entry.date}</div>
                        <div><span className="font-medium">Memo:</span> {match.ledger_entry.memo}</div>
                        <div><span className="font-medium">Amount:</span> 
                          <span className={match.ledger_entry.amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${Math.abs(match.ledger_entry.amount).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Differences */}
                  {(match.amount_difference !== 0 || match.date_difference_days !== 0) && (
                    <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                      <h5 className="font-medium text-yellow-800 mb-2">Differences</h5>
                      <div className="text-sm text-yellow-700 space-y-1">
                        {match.amount_difference !== 0 && (
                          <div>Amount difference: ${Math.abs(match.amount_difference).toFixed(2)}</div>
                        )}
                        {match.date_difference_days !== 0 && (
                          <div>Date difference: {match.date_difference_days} day(s)</div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  {match.status === 'pending' && (
                    <div className="mt-4 flex space-x-3">
                      <button
                        onClick={() => handleApproveMatch(match.id)}
                        className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 flex items-center"
                      >
                        <span className="mr-1">✓</span>
                        Approve Match
                      </button>
                      <button
                        onClick={() => handleRejectMatch(match.id)}
                        className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 flex items-center"
                      >
                        <span className="mr-1">✗</span>
                        Reject Match
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}