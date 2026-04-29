import { useEffect, useState, useRef } from 'react'
import { format, parseISO, differenceInCalendarDays } from 'date-fns'
import { analyticsApi } from '../../services/api'

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v ?? 0)
}

/**
 * Computes burn-rate projection.
 * Per CONTEXT.md D-06 + D-09:
 *   - If date range is fully in the past -> return { in_progress: false, projected: null }.
 *   - Else -> projected = (spent / days_elapsed) * total_days_in_range.
 */
function computeBurnRate(dateFrom, dateTo, currentTotal) {
  if (!dateFrom || !dateTo) return { in_progress: false, projected: null }
  const start = parseISO(dateFrom)
  const end = parseISO(dateTo)
  const today = new Date()
  const totalDays = differenceInCalendarDays(end, start) + 1
  if (totalDays <= 0) return { in_progress: false, projected: null }
  if (today > end) return { in_progress: false, projected: null }
  // today is on/before end, AND on/after start
  const elapsed = today < start ? 0 : differenceInCalendarDays(today, start) + 1
  if (elapsed <= 0) return { in_progress: true, projected: null, days_elapsed: 0, total_days: totalDays }
  const dailyRate = currentTotal / elapsed
  return {
    in_progress: true,
    projected: Math.round(dailyRate * totalDays),
    days_elapsed: elapsed,
    total_days: totalDays,
    end_date: end,
  }
}

export default function BurnRateCard({ granularity, dateFrom, dateTo, currentTotal }) {
  const [limit, setLimit] = useState(null)         // numeric or null
  const [inputValue, setInputValue] = useState('') // string for input field
  const [saving, setSaving] = useState(false)
  const lastFetchedGranularity = useRef(null)

  // Load limit on mount and whenever granularity changes
  useEffect(() => {
    if (lastFetchedGranularity.current === granularity) return
    lastFetchedGranularity.current = granularity
    analyticsApi.getSpendingLimit(granularity)
      .then((res) => {
        const amount = res.data.amount
        setLimit(amount)
        setInputValue(amount != null ? String(amount) : '')
      })
      .catch(() => {})
  }, [granularity])

  async function persistLimit() {
    const trimmed = inputValue.trim()
    setSaving(true)
    try {
      if (trimmed === '') {
        await analyticsApi.deleteSpendingLimit(granularity)
        setLimit(null)
      } else {
        const num = Number(trimmed)
        if (!Number.isFinite(num) || num <= 0) {
          setInputValue(limit != null ? String(limit) : '')
          return
        }
        const res = await analyticsApi.putSpendingLimit({ granularity, amount: num })
        setLimit(res.data.amount)
        setInputValue(String(res.data.amount))
      }
    } catch {
      // Revert on error
      setInputValue(limit != null ? String(limit) : '')
    } finally {
      setSaving(false)
    }
  }

  const burn = computeBurnRate(dateFrom, dateTo, currentTotal)
  const projected = burn.projected
  const overLimit = limit != null && projected != null && projected > limit
  const pctOfLimit = limit != null && limit > 0 ? Math.round((currentTotal / limit) * 100) : null

  return (
    <div className={`card ${overLimit ? 'border-red-300 bg-red-50' : ''}`}>
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">
            {burn.in_progress ? 'Burn-rate projection' : 'Period total (closed)'}
          </p>
          {burn.in_progress && projected != null ? (
            <p className={`text-2xl font-bold mt-1 ${overLimit ? 'text-red-600' : 'text-gray-900'}`}>
              At this rate: {formatINR(projected)}
              {burn.end_date && (
                <span className="text-sm font-normal text-gray-500"> by {format(burn.end_date, 'MMM d')}</span>
              )}
            </p>
          ) : (
            <p className="text-2xl font-bold text-gray-900 mt-1">
              Actual: {formatINR(currentTotal)}
            </p>
          )}
          {limit != null && (
            <p className={`text-xs mt-1 ${overLimit ? 'text-red-600' : 'text-gray-500'}`}>
              {formatINR(currentTotal)} of {formatINR(limit)}
              {pctOfLimit != null && ` (${pctOfLimit}%)`}
            </p>
          )}
        </div>

        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="label">{granularity.charAt(0).toUpperCase() + granularity.slice(1)} Limit (&#8377;)</label>
            <input
              type="number"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onBlur={persistLimit}
              onKeyDown={(e) => { if (e.key === 'Enter') e.target.blur() }}
              disabled={saving}
              placeholder="No limit set"
              min="0"
              step="100"
              className="input-field"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
