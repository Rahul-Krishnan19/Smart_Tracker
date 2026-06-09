import { useEffect, useState, useCallback } from 'react'
import { insightsApi } from '../services/api'
import SubscriptionsSection from '../components/insights/SubscriptionsSection'
import InsightsFeedSection from '../components/insights/InsightsFeedSection'

export default function InsightsPage() {
  const [subs, setSubs] = useState({ items: [], estimated_monthly_total: 0 })
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [s, i] = await Promise.all([
        insightsApi.getSubscriptions(),
        insightsApi.getInsights(),
      ])
      setSubs(s)
      setInsights(i)
    } catch {
      // ignore errors — sections will show empty states
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  if (loading) return <div className="text-slate-500">Loading insights...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Syne, sans-serif' }}>Insights</h1>
        <p className="text-sm text-slate-500 mt-0.5">Patterns, anomalies, and spending intelligence</p>
      </div>
      <SubscriptionsSection data={subs} onUpdate={refresh} />
      <InsightsFeedSection insights={insights} onUpdate={refresh} />
    </div>
  )
}
