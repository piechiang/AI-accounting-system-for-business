import api from './api'
import { Transaction, TransactionUpload, TransactionStats } from '@/types/transaction'

export const transactionService = {
  // Upload transactions file
  uploadTransactions: async (file: File, source: string): Promise<TransactionUpload> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source)
    
    const response = await api.post('/transactions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Get raw transactions
  getRawTransactions: async (params?: {
    skip?: number
    limit?: number
    source?: string
    start_date?: string
    end_date?: string
  }): Promise<Transaction[]> => {
    const response = await api.get('/transactions/raw', { params })
    return response.data
  },

  // Get clean transactions
  getCleanTransactions: async (params?: {
    skip?: number
    limit?: number
    classified_only?: boolean
    reviewed_only?: boolean
  }): Promise<Transaction[]> => {
    const response = await api.get('/transactions/clean', { params })
    return response.data
  },

  // Get transaction statistics
  getTransactionStats: async (): Promise<TransactionStats> => {
    const response = await api.get('/transactions/stats')
    return response.data
  },

  // Delete transaction
  deleteTransaction: async (transactionId: number): Promise<void> => {
    await api.delete(`/transactions/${transactionId}`)
  },
}