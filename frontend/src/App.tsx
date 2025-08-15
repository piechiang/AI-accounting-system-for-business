import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/Toaster'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import Transactions from '@/pages/Transactions'
import Classification from '@/pages/Classification'
import Reconciliation from '@/pages/Reconciliation'
import Export from '@/pages/Export'
import Settings from '@/pages/Settings'

function App() {
  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/classification" element={<Classification />} />
          <Route path="/reconciliation" element={<Reconciliation />} />
          <Route path="/export" element={<Export />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
      <Toaster />
    </>
  )
}

export default App