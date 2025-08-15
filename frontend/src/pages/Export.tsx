import React, { useState } from 'react';
import { toast } from '../components/ui/Toaster';

type ExportFormat = 'quickbooks_journal' | 'quickbooks_expense' | 'xero_bank' | 'xero_manual';

interface ExportStats {
  total_transactions: number;
  classified_transactions: number;
  reconciled_transactions: number;
  ready_for_export: number;
}

export default function Export() {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('quickbooks_journal');
  const [dateRange, setDateRange] = useState({
    start: '2024-01-01',
    end: '2024-01-31'
  });
  const [exporting, setExporting] = useState(false);
  const [stats] = useState<ExportStats>({
    total_transactions: 29,
    classified_transactions: 27,
    reconciled_transactions: 25,
    ready_for_export: 23
  });

  const exportFormats = [
    {
      id: 'quickbooks_journal' as ExportFormat,
      name: 'QuickBooks Journal Entries',
      description: 'Standard journal entries format for QuickBooks import',
      icon: '📊',
      fields: ['Date', 'Account', 'Debits', 'Credits', 'Memo', 'Name']
    },
    {
      id: 'quickbooks_expense' as ExportFormat,
      name: 'QuickBooks Expense Format',
      description: 'Expense transaction format for QuickBooks',
      icon: '💳',
      fields: ['Date', 'Vendor', 'Account', 'Amount', 'Memo', 'Payment Method']
    },
    {
      id: 'xero_bank' as ExportFormat,
      name: 'Xero Bank Transactions',
      description: 'Bank transaction format for Xero import',
      icon: '🏦',
      fields: ['Date', 'Amount', 'Payee', 'Description', 'Reference', 'Account Code']
    },
    {
      id: 'xero_manual' as ExportFormat,
      name: 'Xero Manual Journal',
      description: 'Manual journal entries for Xero',
      icon: '📝',
      fields: ['Date', 'Account Code', 'Description', 'Debit', 'Credit', 'Tax Type']
    }
  ];

  const handleExport = async () => {
    if (stats.ready_for_export === 0) {
      toast.error('No transactions ready for export. Please classify and reconcile transactions first.');
      return;
    }

    setExporting(true);
    try {
      // Mock export process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In production, this would call the export API and download the file
      const formatName = exportFormats.find(f => f.id === selectedFormat)?.name;
      const filename = `export_${selectedFormat}_${dateRange.start}_to_${dateRange.end}.csv`;
      
      // Simulate file download
      toast.success(`Successfully exported ${stats.ready_for_export} transactions to ${filename}`);
      
    } catch (error) {
      toast.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handlePreview = async () => {
    setExporting(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.info('Preview feature coming soon!');
    } catch (error) {
      toast.error('Preview failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Export Data</h1>
        <div className="text-sm text-gray-500">
          Export your processed financial data to accounting software
        </div>
      </div>

      {/* Export Stats */}
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
            <div className="bg-purple-500 rounded-lg p-3">
              <span className="text-white text-2xl">🤖</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Classified</p>
              <p className="text-2xl font-bold text-gray-900">{stats.classified_transactions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-green-500 rounded-lg p-3">
              <span className="text-white text-2xl">🔄</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Reconciled</p>
              <p className="text-2xl font-bold text-gray-900">{stats.reconciled_transactions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="bg-orange-500 rounded-lg p-3">
              <span className="text-white text-2xl">📤</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Ready for Export</p>
              <p className="text-2xl font-bold text-gray-900">{stats.ready_for_export}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Export Configuration */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-6">Export Configuration</h2>
            
            {/* Date Range */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date Range
              </label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={dateRange.start}
                    onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">End Date</label>
                  <input
                    type="date"
                    value={dateRange.end}
                    onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Export Formats */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Export Format
              </label>
              <div className="space-y-3">
                {exportFormats.map((format) => (
                  <div
                    key={format.id}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedFormat === format.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedFormat(format.id)}
                  >
                    <div className="flex items-center">
                      <input
                        type="radio"
                        name="exportFormat"
                        value={format.id}
                        checked={selectedFormat === format.id}
                        onChange={() => setSelectedFormat(format.id)}
                        className="mr-3"
                      />
                      <div className="flex-1">
                        <div className="flex items-center mb-1">
                          <span className="text-xl mr-2">{format.icon}</span>
                          <span className="font-medium text-gray-900">{format.name}</span>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{format.description}</p>
                        <div className="text-xs text-gray-500">
                          Fields: {format.fields.join(', ')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-4">
              <button
                onClick={handlePreview}
                disabled={exporting}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <span className="mr-2">👁️</span>
                Preview
              </button>
              <button
                onClick={handleExport}
                disabled={exporting || stats.ready_for_export === 0}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <span className="mr-2">📤</span>
                {exporting ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </div>
        </div>

        {/* Export Guidelines */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Export Guidelines</h3>
            <div className="space-y-4 text-sm">
              <div className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                <div>
                  <div className="font-medium">Data Validation</div>
                  <div className="text-gray-600">All transactions are validated before export</div>
                </div>
              </div>
              <div className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                <div>
                  <div className="font-medium">Format Compliance</div>
                  <div className="text-gray-600">Exported files meet software requirements</div>
                </div>
              </div>
              <div className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                <div>
                  <div className="font-medium">Error Checking</div>
                  <div className="text-gray-600">Built-in validation prevents import errors</div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-medium text-yellow-800 mb-2">💡 Pro Tips</h4>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• Ensure all transactions are classified before export</li>
              <li>• Review reconciliation matches for accuracy</li>
              <li>• Test with a small date range first</li>
              <li>• Keep a backup of your original data</li>
            </ul>
          </div>

          {stats.ready_for_export < stats.total_transactions && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h4 className="font-medium text-red-800 mb-2">⚠️ Action Required</h4>
              <div className="text-sm text-red-700">
                <div className="mb-2">
                  {stats.total_transactions - stats.classified_transactions} transactions need classification
                </div>
                <div>
                  {stats.classified_transactions - stats.reconciled_transactions} transactions need reconciliation
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}