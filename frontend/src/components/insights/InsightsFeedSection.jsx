import { insightsApi } from '../../services/api'

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function InsightsFeedSection({ insights, onUpdate }) {
  const active = (insights || []).filter(i => i.status === 'active').slice(0, 5)

  async function handleDismiss(id) {
    try {
      await insightsApi.dismissInsight(id)
      onUpdate()
    } catch {
      // ignore
    }
  }

  return (
    <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Insights</h2>
      {active.length === 0 ? (
        <p className="text-gray-500 text-sm">Nothing to highlight today.</p>
      ) : (
        <div className="space-y-3">
          {active.map(i => (
            <div key={i.id} className="border border-gray-100 rounded-lg p-3 relative">
              <button
                className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-lg leading-none w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 transition-colors"
                onClick={() => handleDismiss(i.id)}
                title="Dismiss"
              >
                &times;
              </button>
              <div className="pr-8">
                <div className="font-medium text-gray-900 text-sm">{i.title}</div>
                <div className="text-sm text-gray-600 mt-0.5">{i.body}</div>
                <div className="text-xs text-gray-400 mt-1">{formatDate(i.generated_at)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
