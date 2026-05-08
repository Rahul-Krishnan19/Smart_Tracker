import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { transactionsApi } from '../services/api'
import TransactionList from '../components/transactions/TransactionList'
import TransactionForm from '../components/transactions/TransactionForm'
import FilterPanel from '../components/transactions/FilterPanel'
import GmailSync from '../components/gmail/GmailSync'
import { useFilters } from '../context/FiltersContext'

function formatAmount(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount)
}

export default function TransactionsPage() {
  const [searchParams] = useSearchParams()
  const { txFilters, setTxFilters } = useFilters()
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 50, total_pages: 1 })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [addLoading, setAddLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [summary, setSummary] = useState(null)

  const fetchTransactions = useCallback(async (appliedFilters = txFilters, p = page) => {
    setLoading(true)
    setError('')
    try {
      const res = await transactionsApi.list({ ...appliedFilters, page: p, page_size: 50 })
      setData(res.data)
    } catch {
      setError('Failed to load transactions.')
    } finally {
      setLoading(false)
    }
  }, [txFilters, page])

  const fetchSummary = useCallback(async (appliedFilters = txFilters) => {
    try {
      const res = await transactionsApi.summary(appliedFilters)
      setSummary(res.data)
    } catch {
      // Non-critical
    }
  }, [txFilters])

  // Apply URL params (e.g. from drill-down links) once on mount.
  useEffect(() => {
    const df = searchParams.get('date_from')
    const dt = searchParams.get('date_to')
    if (df || dt) {
      setTxFilters(prev => ({
        ...prev,
        ...(df ? { date_from: df } : {}),
        ...(dt ? { date_to: dt } : {}),
      }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    fetchTransactions()
    fetchSummary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleFilter(newFilters) {
    setTxFilters(newFilters)
    setPage(1)
    fetchTransactions(newFilters, 1)
    fetchSummary(newFilters)
  }

  async function handleAddTransaction(formData) {
    setAddLoading(true)
    setError('')
    setSuccess('')
    try {
      await transactionsApi.create(formData)
      setSuccess('Transaction added!')
      setShowForm(false)
      fetchTransactions()
      fetchSummary()
      setTimeout(() => setSuccess(''), 3000)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to add transaction.')
    } finally {
      setAddLoading(false)
    }
  }

  async function handleExport() {
    try {
      const res = await transactionsApi.export(txFilters)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
      const a = document.createElement('a')
      a.href = url
      a.download = 'transactions.csv'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError('Export failed.')
    }
  }

  function handlePageChange(newPage) {
    setPage(newPage)
    fetchTransactions(txFilters, newPage)
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total Spent</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{formatAmount(summary.total_amount)}</p>
          </div>
          <div className="card text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Transactions</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{summary.transaction_count}</p>
          </div>
          {summary.category_breakdown.slice(0, 2).map((c) => (
            <div key={c.category} className="card text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wider">{c.category}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatAmount(c.total)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Gmail Sync */}
      <div className="card py-3 px-4">
        <GmailSync onSyncComplete={() => { fetchTransactions(); fetchSummary() }} />
      </div>

      {/* Filters */}
      <FilterPanel onFilter={handleFilter} loading={loading} defaultValues={txFilters} />

      {/* Alerts */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}
      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{success}</div>
      )}

      {/* Transaction log */}
      <div className="card p-0 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Transactions</h2>
            <p className="text-xs text-gray-500">
              {summary
                ? `${summary.transaction_count} transactions · ${formatAmount(summary.total_amount)}`
                : `${data.total} total`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="btn-secondary flex items-center gap-2 text-sm py-1.5 px-4"
              title="Export filtered transactions as CSV"
            >
              Export CSV
            </button>
            <button
              onClick={() => setShowForm((s) => !s)}
              className="btn-primary flex items-center gap-2 text-sm py-1.5 px-4"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showForm ? 'Cancel' : 'Add Transaction'}
            </button>
          </div>
        </div>

        {showForm && (
          <div className="px-6 py-4 bg-indigo-50 border-b border-indigo-100">
            <h3 className="text-sm font-semibold text-indigo-900 mb-4">New Transaction</h3>
            <TransactionForm onSubmit={handleAddTransaction} loading={addLoading} />
          </div>
        )}

        <TransactionList
          transactions={data.items}
          onRefresh={() => { fetchTransactions(); fetchSummary() }}
          loading={loading}
        />

        {/* Pagination */}
        {data.total_pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              Page {data.page} of {data.total_pages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(data.page - 1)}
                disabled={data.page <= 1 || loading}
                className="btn-secondary text-sm py-1.5 px-3 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(data.page + 1)}
                disabled={data.page >= data.total_pages || loading}
                className="btn-secondary text-sm py-1.5 px-3 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
