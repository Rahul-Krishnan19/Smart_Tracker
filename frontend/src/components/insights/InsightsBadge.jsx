import { useEffect, useState } from 'react'
import { insightsApi } from '../../services/api'

export default function InsightsBadge() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let cancelled = false
    insightsApi.getSummary()
      .then(r => { if (!cancelled) setCount(r?.anomaly_count || 0) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  if (!count) return null

  return (
    <span className="ml-1.5 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-red-500 text-white text-xs font-semibold">
      {count > 99 ? '99+' : count}
    </span>
  )
}
