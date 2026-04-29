import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { useNavigate, createSearchParams } from 'react-router-dom'

const CATEGORY_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#94a3b8', '#f97316', '#a855f7', '#0ea5e9']

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v ?? 0)
}

export default function TrendChart({ data, categoryOverlay = false }) {
  const navigate = useNavigate()

  function handleChartClick(payload) {
    if (!payload?.activePayload?.[0]) return
    const point = payload.activePayload[0].payload
    if (!point.period_start || !point.period_end) return
    navigate({
      pathname: '/transactions',
      search: createSearchParams({
        date_from: point.period_start,
        date_to: point.period_end,
      }).toString(),
    })
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12 text-sm">
        No transaction data for the selected period.
      </div>
    )
  }

  // Flatten category_totals into top-level keys when overlay is on,
  // so each category becomes its own <Area dataKey="...">.
  const allCategories = categoryOverlay
    ? Array.from(
        new Set(
          data.flatMap((d) => Object.keys(d.category_totals || {}))
        )
      ).sort()
    : []

  const chartData = data.map((d) => {
    const flat = { ...d }
    if (categoryOverlay) {
      allCategories.forEach((cat) => {
        flat[cat] = d.category_totals?.[cat] ?? 0
      })
    }
    return flat
  })

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart
        data={chartData}
        onClick={handleChartClick}
        style={{ cursor: 'pointer' }}
        margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="totalGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
        <XAxis dataKey="period_label" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => formatINR(v)} />
        {categoryOverlay && <Legend wrapperStyle={{ fontSize: 11 }} />}

        {!categoryOverlay && (
          <Area
            type="monotone"
            dataKey="total"
            name="Total"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#totalGradient)"
            dot={{ r: 3, fill: '#6366f1' }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        )}

        {categoryOverlay && allCategories.map((cat, i) => (
          <Area
            key={cat}
            type="monotone"
            dataKey={cat}
            name={cat}
            stackId="categories"
            stroke={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
            fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
            fillOpacity={0.7}
            connectNulls
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
