import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format } from 'date-fns'
import { transactionsApi } from '../../services/api'

// System categories — used as the initial seed for the combobox suggestions
// until the API responds with the user's full set (system + custom).
const DEFAULT_CATEGORIES = ['Rent', 'Groceries', 'Shopping', 'Electricity', 'Food & Dining', 'Transport', 'Entertainment', 'Healthcare', 'Subscriptions', 'Utilities', 'Travel', 'Others']
const PAYMENT_METHODS = ['Credit Card', 'UPI', 'Cash', 'Debit Card', 'Net Banking', 'Others']

const schema = z.object({
  transaction_date: z.string().min(1, 'Date is required'),
  amount: z.string().min(1, 'Amount is required').refine(v => !isNaN(Number(v)) && Number(v) > 0, 'Must be a positive number'),
  description: z.string().min(1, 'Description is required').max(500),
  merchant: z.string().max(255).optional(),
  category: z.string().min(1, 'Category is required'),
  payment_method: z.string().min(1, 'Payment method is required'),
  notes: z.string().max(2000).optional(),
})

export default function TransactionForm({ onSubmit, initialValues, onCancel, loading }) {
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES)

  useEffect(() => {
    transactionsApi.categories()
      .then(r => setCategories(r.data.categories))
      .catch(() => {})
  }, [])

  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    resolver: zodResolver(schema),
    defaultValues: initialValues ?? {
      transaction_date: format(new Date(), 'yyyy-MM-dd'),
      category: 'Others',
      payment_method: 'UPI',
    },
  })

  async function onFormSubmit(data) {
    await onSubmit({
      ...data,
      amount: parseFloat(data.amount),
      merchant: data.merchant || undefined,
      notes: data.notes || undefined,
    })
    if (!initialValues) reset()
  }

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="label">Date *</label>
          <input type="date" {...register('transaction_date')} className="input-field" />
          {errors.transaction_date && <p className="text-red-600 text-xs mt-1">{errors.transaction_date.message}</p>}
        </div>
        <div>
          <label className="label">Amount (₹) *</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            {...register('amount')}
            className="input-field"
            placeholder="0.00"
          />
          {errors.amount && <p className="text-red-600 text-xs mt-1">{errors.amount.message}</p>}
        </div>
      </div>

      <div>
        <label className="label">Description *</label>
        <input {...register('description')} className="input-field" placeholder="What was this for?" />
        {errors.description && <p className="text-red-600 text-xs mt-1">{errors.description.message}</p>}
      </div>

      <div>
        <label className="label">Merchant</label>
        <input {...register('merchant')} className="input-field" placeholder="e.g. Amazon, Swiggy" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="label">Category *</label>
          <input
            list="category-list"
            {...register('category', { required: 'Category is required' })}
            className="input-field"
            placeholder="Select or type a category"
          />
          <datalist id="category-list">
            {categories.map((c) => <option key={c} value={c} />)}
          </datalist>
          {errors.category && <p className="text-red-600 text-xs mt-1">{errors.category.message}</p>}
        </div>
        <div>
          <label className="label">Payment Method *</label>
          <select {...register('payment_method')} className="input-field">
            {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          {errors.payment_method && <p className="text-red-600 text-xs mt-1">{errors.payment_method.message}</p>}
        </div>
      </div>

      <div>
        <label className="label">Notes</label>
        <textarea
          {...register('notes')}
          className="input-field resize-none"
          rows={2}
          placeholder="Optional notes…"
        />
      </div>

      <div className="flex gap-2 justify-end">
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
        )}
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Saving…' : initialValues ? 'Update' : 'Add Transaction'}
        </button>
      </div>
    </form>
  )
}
