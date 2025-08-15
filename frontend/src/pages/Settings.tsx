import React, { useState } from 'react';
import { toast } from '../components/ui/Toaster';

interface Settings {
  apiKeys: {
    openai: string;
    anthropic: string;
  };
  classification: {
    confidenceThreshold: number;
    defaultModel: string;
    autoApproveThreshold: number;
  };
  reconciliation: {
    dateToleranceDays: number;
    fuzzyMatchThreshold: number;
    autoApproveExactMatches: boolean;
  };
  export: {
    defaultFormat: string;
    includeTaxMapping: boolean;
    validateBeforeExport: boolean;
  };
}

export default function Settings() {
  const [settings, setSettings] = useState<Settings>({
    apiKeys: {
      openai: '',
      anthropic: ''
    },
    classification: {
      confidenceThreshold: 0.8,
      defaultModel: 'gpt-3.5-turbo',
      autoApproveThreshold: 0.95
    },
    reconciliation: {
      dateToleranceDays: 3,
      fuzzyMatchThreshold: 0.85,
      autoApproveExactMatches: true
    },
    export: {
      defaultFormat: 'quickbooks_journal',
      includeTaxMapping: true,
      validateBeforeExport: true
    }
  });

  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'api' | 'classification' | 'reconciliation' | 'export'>('api');

  const handleSave = async () => {
    setSaving(true);
    try {
      // Mock save - in production this would save to the backend
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.success('Settings saved successfully');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (provider: 'openai' | 'anthropic') => {
    try {
      // Mock API test
      await new Promise(resolve => setTimeout(resolve, 1500));
      toast.success(`${provider === 'openai' ? 'OpenAI' : 'Anthropic'} connection successful`);
    } catch (error) {
      toast.error(`${provider === 'openai' ? 'OpenAI' : 'Anthropic'} connection failed`);
    }
  };

  const updateSettings = (section: keyof Settings, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <span className="mr-2">💾</span>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {/* Settings Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex">
            {[
              { id: 'api', label: '🔑 API Keys', icon: '🔑' },
              { id: 'classification', label: '🤖 Classification', icon: '🤖' },
              { id: 'reconciliation', label: '🔄 Reconciliation', icon: '🔄' },
              { id: 'export', label: '📤 Export', icon: '📤' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-6 text-sm font-medium border-b-2 ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* API Keys Tab */}
          {activeTab === 'api' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">AI Service API Keys</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Configure your AI service providers for transaction classification. Your API keys are stored securely and never logged.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    OpenAI API Key
                  </label>
                  <div className="flex space-x-3">
                    <input
                      type="password"
                      value={settings.apiKeys.openai}
                      onChange={(e) => updateSettings('apiKeys', 'openai', e.target.value)}
                      placeholder="sk-..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => handleTestConnection('openai')}
                      disabled={!settings.apiKeys.openai}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                      Test
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Used for GPT-based transaction classification
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Anthropic API Key
                  </label>
                  <div className="flex space-x-3">
                    <input
                      type="password"
                      value={settings.apiKeys.anthropic}
                      onChange={(e) => updateSettings('apiKeys', 'anthropic', e.target.value)}
                      placeholder="sk-ant-..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => handleTestConnection('anthropic')}
                      disabled={!settings.apiKeys.anthropic}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                      Test
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Used for Claude-based transaction classification
                  </p>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-medium text-blue-800 mb-2">💡 API Key Management</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• API keys are encrypted before storage</li>
                  <li>• Both providers are used as fallbacks for reliability</li>
                  <li>• You can use either OpenAI or Anthropic (or both)</li>
                  <li>• Rate limits are automatically handled</li>
                </ul>
              </div>
            </div>
          )}

          {/* Classification Tab */}
          {activeTab === 'classification' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">Classification Settings</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Configure how the AI classifies transactions and the confidence thresholds for automation.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confidence Threshold
                  </label>
                  <div className="flex items-center space-x-4">
                    <input
                      type="range"
                      min="0.5"
                      max="1.0"
                      step="0.05"
                      value={settings.classification.confidenceThreshold}
                      onChange={(e) => updateSettings('classification', 'confidenceThreshold', parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium w-12">
                      {(settings.classification.confidenceThreshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Minimum confidence required for automatic classification
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default AI Model
                  </label>
                  <select
                    value={settings.classification.defaultModel}
                    onChange={(e) => updateSettings('classification', 'defaultModel', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Fast, Cost-effective)</option>
                    <option value="gpt-4">GPT-4 (Higher Accuracy)</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet (Balanced)</option>
                    <option value="claude-3-opus">Claude 3 Opus (Highest Accuracy)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Auto-Approve Threshold
                  </label>
                  <div className="flex items-center space-x-4">
                    <input
                      type="range"
                      min="0.85"
                      max="1.0"
                      step="0.01"
                      value={settings.classification.autoApproveThreshold}
                      onChange={(e) => updateSettings('classification', 'autoApproveThreshold', parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium w-12">
                      {(settings.classification.autoApproveThreshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Classifications above this threshold are automatically approved
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Reconciliation Tab */}
          {activeTab === 'reconciliation' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">Reconciliation Settings</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Configure matching algorithms and tolerance levels for bank reconciliation.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date Tolerance (Days)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="14"
                    value={settings.reconciliation.dateToleranceDays}
                    onChange={(e) => updateSettings('reconciliation', 'dateToleranceDays', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Maximum days between transaction and ledger entry dates for matching
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fuzzy Match Threshold
                  </label>
                  <div className="flex items-center space-x-4">
                    <input
                      type="range"
                      min="0.7"
                      max="0.95"
                      step="0.05"
                      value={settings.reconciliation.fuzzyMatchThreshold}
                      onChange={(e) => updateSettings('reconciliation', 'fuzzyMatchThreshold', parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium w-12">
                      {(settings.reconciliation.fuzzyMatchThreshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Minimum similarity score for description-based matching
                  </p>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="autoApproveExact"
                    checked={settings.reconciliation.autoApproveExactMatches}
                    onChange={(e) => updateSettings('reconciliation', 'autoApproveExactMatches', e.target.checked)}
                    className="mr-3"
                  />
                  <label htmlFor="autoApproveExact" className="text-sm font-medium text-gray-700">
                    Auto-approve exact matches
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Export Tab */}
          {activeTab === 'export' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">Export Settings</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Configure default export formats and validation options.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default Export Format
                  </label>
                  <select
                    value={settings.export.defaultFormat}
                    onChange={(e) => updateSettings('export', 'defaultFormat', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="quickbooks_journal">QuickBooks Journal Entries</option>
                    <option value="quickbooks_expense">QuickBooks Expense Format</option>
                    <option value="xero_bank">Xero Bank Transactions</option>
                    <option value="xero_manual">Xero Manual Journal</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="includeTaxMapping"
                      checked={settings.export.includeTaxMapping}
                      onChange={(e) => updateSettings('export', 'includeTaxMapping', e.target.checked)}
                      className="mr-3"
                    />
                    <label htmlFor="includeTaxMapping" className="text-sm font-medium text-gray-700">
                      Include tax category mappings
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="validateBeforeExport"
                      checked={settings.export.validateBeforeExport}
                      onChange={(e) => updateSettings('export', 'validateBeforeExport', e.target.checked)}
                      className="mr-3"
                    />
                    <label htmlFor="validateBeforeExport" className="text-sm font-medium text-gray-700">
                      Validate data before export
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}