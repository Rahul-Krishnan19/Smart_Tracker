import { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { startOfDay, endOfDay, startOfWeek, endOfWeek, startOfMonth, endOfMonth, subMonths, startOfYear, format } from 'date-fns'
import { transactionsApi } from '../../services/api'

const DEFAULT_CATEGORIES = ['Rent', 'Groceries', 'Shopping', 'Electricity', 'Food & Dining', 'Transport', 'Entertainment', 'Healthcare', 'Subscriptions', 'Utilities', 'Travel', 'Others']
const PAYMENT_METHODS = ['Credit Card', 'UPI', 'Cash', 'Debit Card', 'Net Banking', 'Others']

const DATE_PRESETS = [
  { label: 'Today', from: () => startOfDay(new Date()), to: () => endOfDay(new Date()) },
  { label: 'This Week', from: () => startOfWeek(new Date(), { weekStartsOn: 1 }), to: () => endOfWeek(new Date(), { weekStartsOn: 1 }) },
  { label: 'This Month', from: () => startOfMonth(new Date()), to: () => endOfMonth(new Date()) },
  { label: 'Last Month', from: () => startOfMonth(subMonths(new Date(), 1)), to: () => endOfMonth(subMonths(new Date(), 1)) },
  { label: 'Last 3M', from: () => startOfMonth(subMonths(new Date(), 3)), to: () => endOfMonth(new Date()) },
  { label: 'This Year', from: () => startOfYear(new Date()), to: () => endOfDay(new Date()) },
]

export default function FilterPanel({ onFilter, loading, defaultValues = {} }) {
  const { register, handleSubmit, reset, setValue } = useForm({ defaultValues })
  const [paymentSources, setPaymentSources] = useState([])
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES)
  const [merchantSuggestions, setMerchantSuggestions] = useState([])
  const debounceRef = useRef(null)

  useEffect(() => {
    transactionsApi.paymentSources().then(res => setPaymentSources(res.data.payment_sources)).catch(() => {})
    transactionsApi.categories().then(res => setCategories(res.data.categories)).catch(() => {})
  }, [])

  function handleSearchChange(e) {
    const q = e.target.value
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (q.length >= 2) {
      debounceRef.current = setTimeout(() => {
        transactionsApi.merchants(q).then(res => setMerchantSuggestions(res.data.merchants)).catch(() => {})
      }, 300)
    } else {
      setMerchantSuggestions([])
    }
  }

  function applyPreset(preset) {
    setValue('date_from', format(preset.from(), 'yyyy-MM-dd'))
    setValue('date_to', format(preset.to(), 'yyyy-MM-dd'))
  }

  function onSubmit(data) {
    // Remove empty strings
    const filters = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    )
    onFilter(filters)
  }

  function onReset() {
    reset()
    setMerchantSuggestions([])
    onFilter({})
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="label">From</label>
          <input type="date" {...register('date_from')} className="input-field" />
        </div>
        <div>
          <label className="label">To</label>
          <input type="date" {...register('date_to')} className="input-field" />
        </div>
        <div>
          <label className="label">Category</label>
          <select {...register('category')} className="input-field">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Payment Method</label>
          <select {...register('payment_method')} className="input-field">
            <option value="">All methods</option>
            {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Payment Source</label>
          <select {...register('payment_source')} className="input-field">
            <option value="">All sources</option>
            {paymentSources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Min Amount</label>
          <input type="number" {...register('min_amount')} className="input-field" placeholder="0" min="0" step="0.01" />
        </div>
        <div>
          <label className="label">Max Amount</label>
          <input type="number" {...register('max_amount')} className="input-field" placeholder="Any" min="0" step="0.01" />
        </div>
        <div className="relative">
          <label className="label">Search</label>
          <input
            type="text"
            {...register('search')}
            className="input-field"
            placeholder="Description, merchant..."
            maxLength={100}
            onChange={handleSearchChange}
            list="merchant-suggestions"
          />
          <datalist id="merchant-suggestions">
            {merchantSuggestions.map((m) => <option key={m} value={m} />)}
          </datalist>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-2">
        {DATE_PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => applyPreset(p)}
            className="text-xs px-2.5 py-1 rounded-full bg-gray-100 hover:bg-indigo-100 hover:text-indigo-700 text-gray-600 transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="flex gap-2 mt-3">
        <button type="submit" disabled={loading} className="btn-primary text-sm py-1.5 px-4">
          Apply Filters
        </button>
        <button type="button" onClick={onReset} className="btn-secondary text-sm py-1.5 px-4">
          Reset
        </button>
      </div>
    </form>
  )
}
