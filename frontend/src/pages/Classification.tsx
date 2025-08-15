import React, { useState, useEffect } from 'react';
import { toast } from '../components/ui/Toaster';

interface ClassificationRule {
  id: number;
  name: string;
  keyword_regex: string;
  suggested_category: string;
  confidence: number;
  match_count: number;
  success_rate: number;
}

interface UnclassifiedTransaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  suggested_category: string;
  confidence: number;
  ai_reason: string;
}

export default function Classification() {
  const [rules, setRules] = useState<ClassificationRule[]>([]);
  const [unclassifiedTransactions, setUnclassifiedTransactions] = useState<UnclassifiedTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'pending'>('pending');

  useEffect(() => {
    fetchClassificationData();
  }, []);

  const fetchClassificationData = async () => {
    setLoading(true);
    try {
      // Mock data
      const mockRules: ClassificationRule[] = [
        {
          id: 1,
          name: 'Office Supplies',
          keyword_regex: '(STAPLES|OFFICE DEPOT|AMAZON.*OFFICE|SUPPLIES)',
          suggested_category: 'Office Expenses',
          confidence: 0.95,
          match_count: 15,
          success_rate: 0.93
        },
        {
          id: 2,
          name: 'Software & Subscriptions',
          keyword_regex: '(MICROSOFT|ADOBE|GOOGLE|SAAS|SOFTWARE|SUBSCRIPTION)',
          suggested_category: 'Software Expenses',
          confidence: 0.90,
          match_count: 8,
          success_rate: 0.98
        },
        {
          id: 3,
          name: 'Travel',
          keyword_regex: '(AIRLINE|HOTEL|UBER|LYFT|RENTAL CAR|AIRBNB)',
          suggested_category: 'Travel Expenses',
          confidence: 0.90,
          match_count: 12,
          success_rate: 0.87
        },
        {
          id: 4,
          name: 'Meals & Entertainment',
          keyword_regex: '(RESTAURANT|STARBUCKS|MCDONALD|BURGER|PIZZA|COFFEE)',
          suggested_category: 'Meals & Entertainment',
          confidence: 0.85,
          match_count: 22,
          success_rate: 0.89
        }
      ];

      const mockUnclassified: UnclassifiedTransaction[] = [
        {
          id: 101,
          date: '2024-01-15',
          description: 'ZOOM.US VIDEO COMM',
          amount: -14.99,
          suggested_category: 'Software Expenses',
          confidence: 0.92,
          ai_reason: 'Video communication software subscription, commonly used for business meetings'
        },
        {
          id: 102,
          date: '2024-01-14',
          description: 'COSTCO WHOLESALE',
          amount: -156.78,
          suggested_category: 'Office Supplies',
          confidence: 0.78,
          ai_reason: 'Wholesale purchase that could include office supplies or business inventory'
        },
        {
          id: 103,
          date: '2024-01-12',
          description: 'GITHUB INC',
          amount: -21.00,
          suggested_category: 'Software Expenses',
          confidence: 0.96,
          ai_reason: 'Software development platform subscription for code repository hosting'
        }
      ];

      await new Promise(resolve => setTimeout(resolve, 800));
      setRules(mockRules);
      setUnclassifiedTransactions(mockUnclassified);
    } catch (error) {
      toast.error('Failed to load classification data');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveClassification = async (transactionId: number, category: string) => {
    try {
      setUnclassifiedTransactions(prev => 
        prev.filter(t => t.id !== transactionId)
      );
      toast.success(`Transaction classified as ${category}`);
    } catch (error) {
      toast.error('Failed to approve classification');
    }
  };

  const handleRejectClassification = async (transactionId: number) => {
    try {
      // In production, this would open a modal to select the correct category
      toast.info('Please select the correct category for this transaction');
    } catch (error) {
      toast.error('Failed to reject classification');
    }
  };

  const handleRunAIClassification = async () => {
    setLoading(true);
    try {
      // Mock AI classification
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Simulate adding new classified transactions
      const newClassified: UnclassifiedTransaction[] = [
        {
          id: 104,
          date: '2024-01-10',
          description: 'DROPBOX SUBSCRIPTION',
          amount: -12.99,
          suggested_category: 'Software Expenses',
          confidence: 0.94,
          ai_reason: 'Cloud storage service subscription for business file storage and collaboration'
        }
      ];
      
      setUnclassifiedTransactions(prev => [...prev, ...newClassified]);
      toast.success('AI classification completed! Found 1 new classification');
    } catch (error) {
      toast.error('AI classification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">AI Classification</h1>
        <button
          onClick={handleRunAIClassification}
          disabled={loading}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <span className="mr-2">🤖</span>
          {loading ? 'Running AI...' : 'Run AI Classification'}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-blue-500 rounded-lg p-3">
              <span className="text-white text-2xl">📋</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Rules</p>
              <p className="text-2xl font-bold text-gray-900">{rules.length}</p>
              <p className="text-sm text-gray-500">Classification patterns</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-yellow-500 rounded-lg p-3">
              <span className="text-white text-2xl">⏳</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Pending Review</p>
              <p className="text-2xl font-bold text-gray-900">{unclassifiedTransactions.length}</p>
              <p className="text-sm text-gray-500">Need human approval</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-green-500 rounded-lg p-3">
              <span className="text-white text-2xl">🎯</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg. Accuracy</p>
              <p className="text-2xl font-bold text-gray-900">
                {rules.length > 0 ? (rules.reduce((acc, rule) => acc + rule.success_rate, 0) / rules.length * 100).toFixed(1) : 0}%
              </p>
              <p className="text-sm text-gray-500">Overall performance</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex">
            <button
              onClick={() => setActiveTab('pending')}
              className={`py-4 px-6 text-sm font-medium border-b-2 ${
                activeTab === 'pending'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Pending Classifications ({unclassifiedTransactions.length})
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`py-4 px-6 text-sm font-medium border-b-2 ${
                activeTab === 'rules'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Classification Rules ({rules.length})
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'pending' ? (
            <div className="space-y-4">
              {unclassifiedTransactions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-4">🎉</div>
                  <div className="text-lg font-medium mb-2">All caught up!</div>
                  <div>No transactions need classification review.</div>
                </div>
              ) : (
                unclassifiedTransactions.map((transaction) => (
                  <div key={transaction.id} className="border rounded-lg p-4 bg-gray-50">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-medium text-gray-900">{transaction.description}</h3>
                          <span className="text-sm text-gray-500">{transaction.date}</span>
                        </div>
                        <div className="text-lg font-semibold text-red-600 mb-2">
                          -${Math.abs(transaction.amount).toFixed(2)}
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-white rounded-lg p-4 mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center">
                          <span className="text-sm font-medium text-gray-700">AI Suggestion:</span>
                          <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                            {transaction.suggested_category}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span className="text-sm text-gray-500">Confidence:</span>
                          <div className="ml-2 flex items-center">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${transaction.confidence * 100}%` }}
                              ></div>
                            </div>
                            <span className="ml-2 text-sm font-medium">
                              {(transaction.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{transaction.ai_reason}</p>
                      
                      <div className="flex space-x-3">
                        <button
                          onClick={() => handleApproveClassification(transaction.id, transaction.suggested_category)}
                          className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 flex items-center"
                        >
                          <span className="mr-1">✓</span>
                          Approve
                        </button>
                        <button
                          onClick={() => handleRejectClassification(transaction.id)}
                          className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 flex items-center"
                        >
                          <span className="mr-1">✗</span>
                          Reject & Reclassify
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {rules.map((rule) => (
                <div key={rule.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900 mb-1">{rule.name}</h3>
                      <p className="text-sm text-gray-600 mb-2">
                        Maps to: <span className="font-medium">{rule.suggested_category}</span>
                      </p>
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {rule.keyword_regex}
                      </code>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="text-center">
                      <div className="text-lg font-semibold text-blue-600">{rule.match_count}</div>
                      <div className="text-xs text-gray-500">Matches</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-green-600">
                        {(rule.success_rate * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-500">Success Rate</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-purple-600">
                        {(rule.confidence * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-500">Confidence</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}