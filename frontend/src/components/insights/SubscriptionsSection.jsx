import { insightsApi } from '../../services/api'

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
}

function formatMonth(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })
}

export default function SubscriptionsSection({ data, onUpdate }) {
  const items = data?.items || []
  const estimated_monthly_total = data?.estimated_monthly_total || 0

  async function handleToggle(id, currentStatus, e) {
    e.preventDefault()
    const newStatus = currentStatus === 'active' ? 'canceled' : 'active'
    try {
      await insightsApi.updateSubscription(id, newStatus)
      onUpdate()
    } catch {
      // ignore
    }
  }

  return (
    <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-baseline gap-3 mb-3">
        <h2 className="text-lg font-semibold text-gray-900">Subscriptions</h2>
        {items.length > 0 && (
          <span className="text-sm text-gray-500">
            Estimated monthly: {formatINR(estimated_monthly_total)}
          </span>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">No subscriptions detected yet — keep syncing emails.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                <th className="pb-2 pr-4 font-medium">Merchant</th>
                <th className="pb-2 pr-4 font-medium">Typical Amount</th>
                <th className="pb-2 pr-4 font-medium">First Seen</th>
                <th className="pb-2 pr-4 font-medium">Last Seen</th>
                <th className="pb-2 pr-4 font-medium">Status</th>
                <th className="pb-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => (
                <tr key={s.id} className="border-b border-gray-50 last:border-0">
                  <td className="py-2 pr-4 font-medium text-gray-900">{s.merchant}</td>
                  <td className="py-2 pr-4 text-gray-700">{formatINR(s.typical_amount)}</td>
                  <td className="py-2 pr-4 text-gray-500">{formatMonth(s.first_seen_month)}</td>
                  <td className="py-2 pr-4 text-gray-500">{formatMonth(s.last_seen_month)}</td>
                  <td className="py-2 pr-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      s.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="py-2">
                    <button
                      className={`text-xs px-2.5 py-1 rounded border transition-colors ${
                        s.status === 'active'
                          ? 'border-red-200 text-red-600 hover:bg-red-50'
                          : 'border-green-200 text-green-600 hover:bg-green-50'
                      }`}
                      onClick={(e) => handleToggle(s.id, s.status, e)}
                    >
                      {s.status === 'active' ? 'Cancel' : 'Reactivate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
