import { useState } from 'react'
import { format } from 'date-fns'
import TransactionForm from './TransactionForm'
import { transactionsApi } from '../../services/api'

const CATEGORY_COLORS = {
  'Rent': 'bg-blue-100 text-blue-800',
  'Groceries': 'bg-green-100 text-green-800',
  'Shopping': 'bg-purple-100 text-purple-800',
  'Electricity': 'bg-yellow-100 text-yellow-800',
  'Food & Dining': 'bg-orange-100 text-orange-800',
  'Transport': 'bg-cyan-100 text-cyan-800',
  'Entertainment': 'bg-pink-100 text-pink-800',
  'Healthcare': 'bg-red-100 text-red-800',
  'Subscriptions': 'bg-teal-100 text-teal-800',
  'Utilities': 'bg-amber-100 text-amber-800',
  'Travel': 'bg-sky-100 text-sky-800',
  'Others': 'bg-gray-100 text-gray-800',
}

const PAYMENT_ICONS = {
  'Credit Card': '💳',
  'UPI': '📱',
  'Cash': '💵',
  'Debit Card': '🏦',
  'Net Banking': '🌐',
  'Others': '💰',
}

const CATEGORIES = ['Rent', 'Groceries', 'Shopping', 'Electricity', 'Food & Dining', 'Transport', 'Entertainment', 'Healthcare', 'Subscriptions', 'Utilities', 'Travel', 'Others']

function formatAmount(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount)
}

export default function TransactionList({ transactions, onRefresh, loading, onBulkCategorize }) {
  const [editingId, setEditingId] = useState(null)
  const [editLoading, setEditLoading] = useState(false)
  const [deleteId, setDeleteId] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [categoryEdit, setCategoryEdit] = useState(null) // { txId, value }
  const [categoryEditLoading, setCategoryEditLoading] = useState(false)
  const [bulkCategory, setBulkCategory] = useState('')

  function toggleSelectAll() {
    if (selectedIds.size === transactions.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(transactions.map(t => t.id)))
    }
  }

  function toggleSelect(id) {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }

  async function saveCategoryEdit(tx) {
    setCategoryEditLoading(true)
    try {
      await transactionsApi.updateCategory(tx.id, {
        category: categoryEdit.value,
      })
      setCategoryEdit(null)
      onRefresh()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update category')
    } finally {
      setCategoryEditLoading(false)
    }
  }

  async function handleBulkCategorize() {
    if (!bulkCategory || selectedIds.size === 0) return
    try {
      await transactionsApi.bulkCategorize({
        transaction_ids: Array.from(selectedIds),
        category: bulkCategory,
      })
      setSelectedIds(new Set())
      setBulkCategory('')
      onRefresh()
    } catch (e) {
      alert(e.response?.data?.detail || 'Bulk update failed')
    }
  }

  async function handleUpdate(id, data) {
    setEditLoading(true)
    try {
      await transactionsApi.update(id, data)
      setEditingId(null)
      onRefresh()
    } catch (e) {
      alert(e.response?.data?.detail || 'Update failed')
    } finally {
      setEditLoading(false)
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this transaction?')) return
    setDeleteId(id)
    try {
      await transactionsApi.delete(id)
      onRefresh()
    } catch {
      alert('Delete failed')
    } finally {
      setDeleteId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        <svg className="animate-spin w-6 h-6 mr-2" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        Loading...
      </div>
    )
  }

  if (!transactions?.length) {
    return (
      <div className="text-center py-16 text-gray-400">
        <svg className="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p>No transactions found.</p>
        <p className="text-sm">Add your first transaction above.</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden">
      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 bg-indigo-50 border-b border-indigo-100">
          <span className="text-sm text-indigo-700 font-medium">{selectedIds.size} selected</span>
          <select
            value={bulkCategory}
            onChange={e => setBulkCategory(e.target.value)}
            className="input-field text-sm py-1 w-40"
          >
            <option value="">Set category...</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button
            onClick={handleBulkCategorize}
            disabled={!bulkCategory}
            className="btn-primary text-sm py-1 px-3 disabled:opacity-40"
          >
            Apply
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        </div>
      )}

      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="px-4 py-3 w-8">
              <input
                type="checkbox"
                checked={transactions.length > 0 && selectedIds.size === transactions.length}
                onChange={toggleSelectAll}
                className="rounded border-gray-300"
              />
            </th>
            <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Date</th>
            <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Description</th>
            <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Category</th>
            <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Method</th>
            <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Amount</th>
            <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {transactions.map((tx) => (
            editingId === tx.id ? (
              <tr key={tx.id}>
                <td colSpan={7} className="px-4 py-4 bg-indigo-50">
                  <TransactionForm
                    initialValues={{
                      transaction_date: tx.transaction_date,
                      amount: String(tx.amount),
                      description: tx.description,
                      merchant: tx.merchant ?? '',
                      category: tx.category,
                      payment_method: tx.payment_method,
                      notes: tx.notes ?? '',
                    }}
                    onSubmit={(data) => handleUpdate(tx.id, data)}
                    onCancel={() => setEditingId(null)}
                    loading={editLoading}
                  />
                </td>
              </tr>
            ) : (
              <tr key={tx.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(tx.id)}
                    onChange={() => toggleSelect(tx.id)}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                  {format(new Date(tx.transaction_date), 'dd MMM yyyy')}
                </td>
                <td className="px-4 py-3 max-w-xs">
                  <div className="text-sm font-medium text-gray-900 truncate">{tx.description}</div>
                  {tx.merchant && <div className="text-xs text-gray-400 truncate">{tx.merchant}</div>}
                  {tx.payment_source && <div className="text-xs text-gray-400 truncate">{tx.payment_source}</div>}
                  {tx.notes && <div className="text-xs text-gray-400 italic truncate">{tx.notes}</div>}
                </td>
                <td className="px-4 py-3">
                  {categoryEdit?.txId === tx.id ? (
                    <div className="flex flex-col gap-1">
                      <select
                        value={categoryEdit.value}
                        onChange={e => setCategoryEdit({ ...categoryEdit, value: e.target.value })}
                        className="input-field text-xs py-0.5"
                      >
                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                      <div className="flex gap-1">
                        <button onClick={() => saveCategoryEdit(tx)} disabled={categoryEditLoading} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Save</button>
                        <button onClick={() => setCategoryEdit(null)} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <span
                      className={`badge cursor-pointer ${CATEGORY_COLORS[tx.category] ?? 'bg-gray-100 text-gray-800'}`}
                      onClick={() => setCategoryEdit({ txId: tx.id, value: tx.category })}
                      title="Click to re-categorize"
                    >
                      {tx.category}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  <span title={tx.payment_method}>
                    {PAYMENT_ICONS[tx.payment_method] ?? '💰'} {tx.payment_method}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900 whitespace-nowrap">
                  {formatAmount(tx.amount)}
                </td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <button
                    onClick={() => setEditingId(tx.id)}
                    className="text-indigo-600 hover:text-indigo-800 text-sm mr-3 font-medium"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(tx.id)}
                    disabled={deleteId === tx.id}
                    className="text-red-500 hover:text-red-700 text-sm font-medium disabled:opacity-50"
                  >
                    {deleteId === tx.id ? '...' : 'Delete'}
                  </button>
                </td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  )
}
