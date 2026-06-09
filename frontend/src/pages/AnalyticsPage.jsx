import { useState, useEffect } from 'react'
import { transactionsApi, analyticsApi } from '../services/api'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import TrendChart from '../components/analytics/TrendChart'
import GranularityToggle from '../components/analytics/GranularityToggle'
import FilterPanel from '../components/transactions/FilterPanel'
import { useFilters } from '../context/FiltersContext'

const CATEGORY_COLORS = {
  'Food & Dining': '#f97316',
  'Transport': '#0ea5e9',
  'Groceries': '#10b981',
  'Shopping': '#8b5cf6',
  'Entertainment': '#ec4899',
  'Healthcare': '#f43f5e',
  'Subscriptions': '#6366f1',
  'Utilities': '#f59e0b',
  'Rent': '#14b8a6',
  'Travel': '#06b6d4',
  'Others': '#94a3b8',
}
const COLORS = ['#f97316', '#0ea5e9', '#10b981', '#8b5cf6', '#ec4899', '#f43f5e', '#6366f1', '#f59e0b', '#14b8a6', '#06b6d4', '#94a3b8']

function getCategoryColor(cat, idx) {
  return CATEGORY_COLORS[cat] || COLORS[idx % COLORS.length]
}

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
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Syne, sans-serif' }}>Analytics</h1>
        <p className="text-sm text-slate-500 mt-0.5">Understand where your money goes</p>
      </div>

      {/* Full filter panel — same component used on the Transactions page.
          Filter state lives in FiltersContext so it persists across tab switches. */}
      <FilterPanel onFilter={handleApply} loading={loading} defaultValues={analyticsFilters} />

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="card border-l-4 border-l-emerald-500">
            <p className="section-label text-slate-400 mb-2">Total Spent</p>
            <p className="stat-number text-2xl">{formatINR(summary.total_amount)}</p>
            {pctChange != null && (
              <span
                className={`inline-flex items-center gap-1 text-xs font-medium mt-2 ${pctChange > 0 ? 'text-red-500' : 'text-emerald-500'}`}
                title={`Previous period: ${formatINR(previousTotal)}`}
              >
                {pctChange > 0 ? '▲' : '▼'} {Math.abs(pctChange).toFixed(1)}% vs last period
              </span>
            )}
          </div>
          <div className="card border-l-4 border-l-sky-400">
            <p className="section-label text-slate-400 mb-2">Transactions</p>
            <p className="stat-number text-2xl">{summary.transaction_count}</p>
          </div>
          <div className="card border-l-4 border-l-violet-400">
            <p className="section-label text-slate-400 mb-2">Avg per Transaction</p>
            <p className="stat-number text-2xl">
              {summary.transaction_count > 0 ? formatINR(summary.total_amount / summary.transaction_count) : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Trend Chart */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
          <div>
            <h2 className="text-base font-bold text-slate-900" style={{ fontFamily: 'Syne, sans-serif' }}>Spending Over Time</h2>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={categoryOverlay}
                onChange={(e) => setCategoryOverlay(e.target.checked)}
                className="accent-emerald-500 w-3.5 h-3.5"
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Category Donut */}
            {summary.category_breakdown.length > 0 && (
              <div className="card">
                <h2 className="text-base font-bold text-slate-900 mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>Spending by Category</h2>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={summary.category_breakdown}
                      dataKey="total"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={2}
                    >
                      {summary.category_breakdown.map((entry, i) => (
                        <Cell key={i} fill={getCategoryColor(entry.category, i)} strokeWidth={0} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', fontFamily: 'IBM Plex Mono' }} />
                    <Legend iconType="circle" iconSize={8} formatter={(value) => <span style={{ fontFamily: 'DM Sans', fontSize: 12, color: '#64748b' }}>{value}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Payment Method Bar */}
            {summary.payment_breakdown.length > 0 && (
              <div className="card">
                <h2 className="text-base font-bold text-slate-900 mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>By Payment Method</h2>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={summary.payment_breakdown} layout="vertical" margin={{ left: 0, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="payment_method" width={96} tick={{ fontSize: 12, fill: '#64748b', fontFamily: 'DM Sans' }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', fontFamily: 'IBM Plex Mono' }} />
                    <Bar dataKey="total" name="Amount" fill="#10b981" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Category breakdown table */}
          {summary.category_breakdown.length > 0 && (
            <div className="card">
              <h2 className="text-base font-bold text-slate-900 mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>Category Breakdown</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      <th className="text-left section-label py-2 font-semibold">Category</th>
                      <th className="text-right section-label py-2 font-semibold">Txns</th>
                      <th className="text-right section-label py-2 font-semibold">Amount</th>
                      <th className="text-right section-label py-2 font-semibold hidden sm:table-cell">Share</th>
                      <th className="hidden sm:table-cell py-2 w-32"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {summary.category_breakdown
                      .sort((a, b) => b.total - a.total)
                      .map((row, i) => {
                        const color = getCategoryColor(row.category, i)
                        const pct = summary.total_amount > 0 ? (row.total / summary.total_amount) * 100 : 0
                        return (
                          <tr key={row.category} className="hover:bg-slate-50/80 transition-colors">
                            <td className="py-3 flex items-center gap-2.5">
                              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                              <span className="font-medium text-slate-800">{row.category}</span>
                            </td>
                            <td className="py-3 text-right text-slate-500">{row.count}</td>
                            <td className="py-3 text-right mono-amount text-slate-900">{formatINR(row.total)}</td>
                            <td className="py-3 text-right text-slate-400 hidden sm:table-cell">{pct.toFixed(1)}%</td>
                            <td className="py-3 hidden sm:table-cell">
                              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Merchant table */}
          {merchantData && merchantData.merchants.length > 0 && (
            <div className="card" id="merchant-breakdown">
              <h2 className="text-base font-bold text-slate-900 mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>Top Merchants by Spend</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      <th className="text-left section-label py-2 font-semibold w-8">#</th>
                      <th className="text-left section-label py-2 font-semibold">Merchant</th>
                      <th className="text-right section-label py-2 font-semibold">Total</th>
                      <th className="text-right section-label py-2 font-semibold hidden sm:table-cell">Txns</th>
                      <th className="text-right section-label py-2 font-semibold hidden md:table-cell">Avg</th>
                      <th className="text-right section-label py-2 font-semibold hidden md:table-cell">%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {merchantData.merchants.map((row, i) => (
                      <tr key={row.merchant} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3">
                          <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center" style={{ fontFamily: 'IBM Plex Mono' }}>
                            {i + 1}
                          </span>
                        </td>
                        <td className="py-3 font-semibold text-slate-900">{row.merchant}</td>
                        <td className="py-3 text-right mono-amount text-slate-900">{formatINR(row.total)}</td>
                        <td className="py-3 text-right text-slate-500 hidden sm:table-cell">{row.count}</td>
                        <td className="py-3 text-right text-slate-400 mono-amount hidden md:table-cell">{formatINR(row.avg)}</td>
                        <td className="py-3 text-right text-slate-400 hidden md:table-cell">{row.pct_of_total.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {merchantData && merchantData.merchants.length === 0 && summary && summary.transaction_count > 0 && (
            <div className="card text-center text-slate-400 py-8 text-sm">
              No merchant data for the selected period.
            </div>
          )}

          {summary.category_breakdown.length === 0 && (
            <div className="card text-center text-slate-400 py-16">
              <p className="text-lg mb-1">No data yet</p>
              <p className="text-sm">No transactions found for the selected period.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
