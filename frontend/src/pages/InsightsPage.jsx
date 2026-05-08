import { useEffect, useState, useCallback } from 'react'
import { insightsApi } from '../services/api'
import AlertsSection from '../components/insights/AlertsSection'
import SubscriptionsSection from '../components/insights/SubscriptionsSection'
import InsightsFeedSection from '../components/insights/InsightsFeedSection'

export default function InsightsPage() {
  const [anomalies, setAnomalies] = useState([])
  const [subs, setSubs] = useState({ items: [], estimated_monthly_total: 0 })
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [a, s, i] = await Promise.all([
        insightsApi.getAnomalies(),
        insightsApi.getSubscriptions(),
        insightsApi.getInsights(),
      ])
      setAnomalies(a)
      setSubs(s)
      setInsights(i)
    } catch {
      // ignore errors — sections will show empty states
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  if (loading) return <div className="text-gray-500">Loading insights...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
      <AlertsSection anomalies={anomalies} onUpdate={refresh} />
      <SubscriptionsSection data={subs} onUpdate={refresh} />
      <InsightsFeedSection insights={insights} onUpdate={refresh} />
    </div>
  )
}
