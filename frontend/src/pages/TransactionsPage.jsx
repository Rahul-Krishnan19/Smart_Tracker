import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { transactionsApi } from '../services/api'
import TransactionList from '../components/transactions/TransactionList'
import TransactionForm from '../components/transactions/TransactionForm'
import FilterPanel from '../components/transactions/FilterPanel'
import GmailSync from '../components/gmail/GmailSync'
import { useFilters } from '../context/FiltersContext'

const CATEGORY_COLORS = {
  'Food & Dining': '#f97316', 'Transport': '#0ea5e9', 'Groceries': '#10b981',
  'Shopping': '#8b5cf6', 'Entertainment': '#ec4899', 'Healthcare': '#f43f5e',
  'Subscriptions': '#6366f1', 'Utilities': '#f59e0b', 'Rent': '#14b8a6',
  'Travel': '#06b6d4', 'Others': '#94a3b8',
}

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
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Syne, sans-serif' }}>Transactions</h1>
          <p className="text-sm text-slate-500 mt-0.5">Your complete spending log</p>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="card border-l-4 border-l-emerald-500">
            <p className="section-label text-slate-400 mb-2">Total Spent</p>
            <p className="stat-number text-xl">{formatAmount(summary.total_amount)}</p>
          </div>
          <div className="card border-l-4 border-l-sky-400">
            <p className="section-label text-slate-400 mb-2">Transactions</p>
            <p className="stat-number text-xl">{summary.transaction_count}</p>
          </div>
          {summary.category_breakdown.slice(0, 2).map((c) => (
            <div key={c.category} className="card border-l-4" style={{ borderLeftColor: CATEGORY_COLORS[c.category] || '#94a3b8' }}>
              <p className="section-label text-slate-400 mb-2 truncate">{c.category}</p>
              <p className="stat-number text-xl">{formatAmount(c.total)}</p>
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
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          {success}
        </div>
      )}

      {/* Transaction log */}
      <div className="card p-0 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900" style={{ fontFamily: 'Syne, sans-serif' }}>All Transactions</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {summary
                ? `${summary.transaction_count} transactions · ${formatAmount(summary.total_amount)}`
                : `${data.total} total`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleExport} className="btn-secondary flex items-center gap-1.5" title="Export filtered transactions as CSV">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              Export CSV
            </button>
            <button onClick={() => setShowForm((s) => !s)} className="btn-primary flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
              {showForm ? 'Cancel' : 'Add'}
            </button>
          </div>
        </div>

        {showForm && (
          <div className="px-6 py-5 bg-emerald-50/50 border-b border-emerald-100">
            <h3 className="text-sm font-bold text-slate-900 mb-4" style={{ fontFamily: 'Syne, sans-serif' }}>New Transaction</h3>
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
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
            <p className="text-sm text-slate-500">Page {data.page} of {data.total_pages}</p>
            <div className="flex gap-2">
              <button onClick={() => handlePageChange(data.page - 1)} disabled={data.page <= 1 || loading} className="btn-secondary text-sm py-1.5 px-3 disabled:opacity-40">← Prev</button>
              <button onClick={() => handlePageChange(data.page + 1)} disabled={data.page >= data.total_pages || loading} className="btn-secondary text-sm py-1.5 px-3 disabled:opacity-40">Next →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
