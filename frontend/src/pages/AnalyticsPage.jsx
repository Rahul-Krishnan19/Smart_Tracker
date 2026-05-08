import { useState, useEffect } from 'react'
import { transactionsApi, analyticsApi } from '../services/api'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import TrendChart from '../components/analytics/TrendChart'
import GranularityToggle from '../components/analytics/GranularityToggle'
import { useFilters } from '../context/FiltersContext'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#94a3b8']

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}

// Build a clean params object for API calls — only include non-empty values.
function buildParams(filters, extras = {}) {
  const params = { ...extras }
  for (const [k, v] of Object.entries(filters)) {
    if (v !== '' && v !== null && v !== undefined) params[k] = v
  }
  return params
}

export default function AnalyticsPage() {
  const { analyticsFilters, setAnalyticsFilters } = useFilters()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [merchantData, setMerchantData] = useState(null)
  const [granularity, setGranularity] = useState('monthly')
  const [trendData, setTrendData] = useState(null)
  const [pctChange, setPctChange] = useState(null)
  const [previousTotal, setPreviousTotal] = useState(0)
  const [categoryOverlay, setCategoryOverlay] = useState(false)
  const [paymentSources, setPaymentSources] = useState([])

  async function fetchSummary(filters = analyticsFilters) {
    setLoading(true)
    try {
      const res = await transactionsApi.summary(buildParams(filters))
      setSummary(res.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  async function fetchMerchantBreakdown(filters = analyticsFilters) {
    try {
      const res = await transactionsApi.merchantBreakdown(buildParams(filters))
      setMerchantData(res.data)
    } catch {
      // ignore
    }
  }

  async function fetchTrend(currentGranularity = granularity, filters = analyticsFilters) {
    try {
      const res = await analyticsApi.trend(buildParams(filters, { granularity: currentGranularity }))
      setTrendData(res.data.trend)
      setPctChange(res.data.pct_change)
      setPreviousTotal(res.data.previous_total)
    } catch {
      setTrendData([])
      setPctChange(null)
      setPreviousTotal(0)
    }
  }

  function handleApply(newFilters) {
    setAnalyticsFilters(newFilters)
    fetchSummary(newFilters)
    fetchMerchantBreakdown(newFilters)
    fetchTrend(granularity, newFilters)
  }

  // Fetch payment sources on mount (used by the Payment Source dropdown)
  useEffect(() => {
    transactionsApi.paymentSources()
      .then(res => setPaymentSources(res.data.payment_sources))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchSummary()
    fetchMerchantBreakdown()
    fetchTrend()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    fetchTrend(granularity)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [granularity])

  return (
    <div className="space-y-6">
      {/* Date Range Picker + Payment Source Filter */}
      <div className="card">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="label">From</label>
            <input
              type="date"
              value={analyticsFilters.date_from}
              onChange={e => setAnalyticsFilters({ ...analyticsFilters, date_from: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">To</label>
            <input
              type="date"
              value={analyticsFilters.date_to}
              onChange={e => setAnalyticsFilters({ ...analyticsFilters, date_to: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">Payment Source</label>
            <select
              value={analyticsFilters.payment_source}
              onChange={e => setAnalyticsFilters({ ...analyticsFilters, payment_source: e.target.value })}
              className="input-field"
            >
              <option value="">All sources</option>
              {paymentSources.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <button onClick={() => handleApply(analyticsFilters)} disabled={loading} className="btn-primary">
            {loading ? 'Loading…' : 'Apply'}
          </button>
        </div>
      </div>

      {/* Trend section (Phase 6) */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-gray-700">Spending over time</h3>
            {pctChange != null && (
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  pctChange > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                }`}
                title={`Previous period: ${new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(previousTotal)}`}
              >
                {pctChange > 0 ? '▲' : '▼'} {Math.abs(pctChange).toFixed(1)}% vs last period
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={categoryOverlay}
                onChange={(e) => setCategoryOverlay(e.target.checked)}
              />
              Category overlay
            </label>
            <GranularityToggle value={granularity} onChange={setGranularity} />
          </div>
        </div>
        <TrendChart data={trendData ?? []} categoryOverlay={categoryOverlay} />
      </div>

      {summary && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="card text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Total Spent</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatINR(summary.total_amount)}</p>
            </div>
            <div className="card text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Transactions</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{summary.transaction_count}</p>
            </div>
            <div className="card text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Avg per Transaction</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {summary.transaction_count > 0
                  ? formatINR(summary.total_amount / summary.transaction_count)
                  : '—'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Category Breakdown — Pie Chart */}
            {summary.category_breakdown.length > 0 && (
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Spending by Category</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={summary.category_breakdown}
                      dataKey="total"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {summary.category_breakdown.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatINR(v)} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Payment Method Breakdown — Bar Chart */}
            {summary.payment_breakdown.length > 0 && (
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Spending by Payment Method</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={summary.payment_breakdown} layout="vertical" margin={{ left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="payment_method" width={90} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v) => formatINR(v)} />
                    <Bar dataKey="total" name="Amount" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Category detail table */}
          {summary.category_breakdown.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Category Breakdown</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left font-semibold text-gray-500 py-2">Category</th>
                      <th className="text-right font-semibold text-gray-500 py-2">Transactions</th>
                      <th className="text-right font-semibold text-gray-500 py-2">Amount</th>
                      <th className="text-right font-semibold text-gray-500 py-2">% of Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {summary.category_breakdown
                      .sort((a, b) => b.total - a.total)
                      .map((row, i) => (
                        <tr key={row.category} className="hover:bg-gray-50">
                          <td className="py-2 flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full inline-block" style={{ background: COLORS[i % COLORS.length] }} />
                            {row.category}
                          </td>
                          <td className="py-2 text-right text-gray-500">{row.count}</td>
                          <td className="py-2 text-right font-medium">{formatINR(row.total)}</td>
                          <td className="py-2 text-right text-gray-500">
                            {summary.total_amount > 0
                              ? `${((row.total / summary.total_amount) * 100).toFixed(1)}%`
                              : '—'}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Merchant Breakdown — Top 10 by spend */}
          {merchantData && merchantData.merchants.length > 0 && (
            <div className="card" id="merchant-breakdown">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Merchants by Spend</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left font-semibold text-gray-500 py-2">#</th>
                      <th className="text-left font-semibold text-gray-500 py-2">Merchant</th>
                      <th className="text-right font-semibold text-gray-500 py-2">Total Spend</th>
                      <th className="text-right font-semibold text-gray-500 py-2">Transactions</th>
                      <th className="text-right font-semibold text-gray-500 py-2">Avg per Txn</th>
                      <th className="text-right font-semibold text-gray-500 py-2">% of Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {merchantData.merchants.map((row, i) => (
                      <tr key={row.merchant} className="hover:bg-gray-50">
                        <td className="py-2 text-gray-400">{i + 1}</td>
                        <td className="py-2 font-medium text-gray-900">{row.merchant}</td>
                        <td className="py-2 text-right font-medium">{formatINR(row.total)}</td>
                        <td className="py-2 text-right text-gray-500">{row.count}</td>
                        <td className="py-2 text-right text-gray-500">{formatINR(row.avg)}</td>
                        <td className="py-2 text-right text-gray-500">{row.pct_of_total.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {merchantData && merchantData.merchants.length === 0 && summary && summary.transaction_count > 0 && (
            <div className="card text-center text-gray-400 py-8 text-sm">
              No merchant data for the selected period.
            </div>
          )}

          {summary.category_breakdown.length === 0 && (
            <div className="card text-center text-gray-400 py-12">
              No transaction data for the selected period.
            </div>
          )}
        </>
      )}
    </div>
  )
}
