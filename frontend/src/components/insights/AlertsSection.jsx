import { useNavigate } from 'react-router-dom'
import { insightsApi } from '../../services/api'

const SEVERITY_PILL = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-gray-100 text-gray-600',
}

function humanize(ruleName) {
  return ruleName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AlertsSection({ anomalies, onUpdate }) {
  const navigate = useNavigate()
  const newAnomalies = (anomalies || []).filter(a => a.status === 'new')

  async function handleAction(id, status, e) {
    e.stopPropagation()
    try {
      await insightsApi.updateAnomaly(id, status)
      onUpdate()
    } catch {
      // ignore
    }
  }

  return (
    <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Alerts</h2>
      {newAnomalies.length === 0 ? (
        <p className="text-gray-500 text-sm">No alerts — your spending looks normal.</p>
      ) : (
        <div className="space-y-3">
          {newAnomalies.map(a => (
            <div
              key={a.id}
              className={`border border-gray-100 rounded-lg p-3 ${a.transaction_id ? 'cursor-pointer hover:bg-gray-50 transition-colors' : ''}`}
              onClick={a.transaction_id ? () => navigate(`/transactions?tx_id=${a.transaction_id}`) : undefined}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 text-sm">{humanize(a.rule_name)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_PILL[a.severity] || SEVERITY_PILL.low}`}>
                      {a.severity}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{formatDate(a.detected_at)}</div>
                  {a.notes && <div className="text-sm text-gray-600 mt-1">{a.notes}</div>}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    className="text-xs px-2.5 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-100 transition-colors"
                    onClick={(e) => handleAction(a.id, 'investigating', e)}
                  >
                    Investigate
                  </button>
                  <button
                    className="text-xs px-2.5 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                    onClick={(e) => handleAction(a.id, 'dismissed', e)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
