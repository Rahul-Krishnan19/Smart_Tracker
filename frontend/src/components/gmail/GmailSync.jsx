import { useState, useEffect } from 'react'
import api from '../../services/api'

function formatIST(isoString) {
  if (!isoString) return null
  return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
}

export default function GmailSync({ onSyncComplete }) {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [result, setSyncResult] = useState(null)
  const [error, setError] = useState('')
  const [lastSyncedAt, setLastSyncedAt] = useState(null)
  const [syncEnabled, setSyncEnabled] = useState(false)
  const [syncIntervalHours, setSyncIntervalHours] = useState(24)
  const [savingSettings, setSavingSettings] = useState(false)

  useEffect(() => {
    api.get('/gmail/status')
      .then(r => {
        setConnected(r.data.connected)
        setLastSyncedAt(r.data.last_synced_at)
        setSyncEnabled(r.data.sync_enabled)
        if (r.data.sync_interval_hours) setSyncIntervalHours(r.data.sync_interval_hours)
      })
      .catch(() => {})

    const params = new URLSearchParams(window.location.search)
    if (params.get('gmail') === 'connected') {
      setConnected(true)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  async function handleConnect() {
    setError('')
    setConnecting(true)
    try {
      const res = await api.get('/gmail/auth-url')
      window.location.href = res.data.auth_url
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to get Google auth URL. Is the backend running?')
      setConnecting(false)
    }
  }

  async function handleSync() {
    setError('')
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await api.post('/gmail/sync?max_emails=50')
      setSyncResult(res.data)
      if (res.data.transactions_created > 0) onSyncComplete?.()
      // Refresh status to get updated last_synced_at
      api.get('/gmail/status').then(r => setLastSyncedAt(r.data.last_synced_at)).catch(() => {})
    } catch (e) {
      setError(e.response?.data?.detail || 'Sync failed. Please try again.')
    } finally {
      setSyncing(false)
    }
  }

  async function handleDisconnect() {
    setError('')
    try {
      await api.delete('/gmail/disconnect')
      setConnected(false)
      setSyncResult(null)
      setSyncEnabled(false)
      setLastSyncedAt(null)
    } catch (e) {
      setError('Failed to disconnect.')
    }
  }

  async function handleSaveSettings(enabled, hours) {
    setSavingSettings(true)
    setError('')
    try {
      const res = await api.put('/gmail/settings', {
        sync_enabled: enabled,
        sync_interval_hours: enabled ? hours : null,
      })
      setSyncEnabled(res.data.sync_enabled)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save sync settings.')
    } finally {
      setSavingSettings(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 flex-wrap">
        {!connected ? (
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            {connecting ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
              </svg>
            )}
            {connecting ? 'Opening Google…' : 'Connect Gmail'}
          </button>
        ) : (
          <>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="btn-primary flex items-center gap-2 text-sm py-1.5 px-4"
            >
              <svg className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {syncing ? 'Syncing…' : 'Sync Emails'}
            </button>
            {lastSyncedAt && (
              <span className="text-xs text-gray-500">
                Last updated at {formatIST(lastSyncedAt)}
              </span>
            )}
            <span className="text-xs text-green-600 font-medium flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full inline-block"></span>
              Gmail connected
            </span>
            <button onClick={handleDisconnect} className="text-xs text-gray-400 hover:text-red-500 underline">
              Disconnect
            </button>
          </>
        )}
      </div>

      {connected && (
        <div className="flex items-center gap-3 flex-wrap mt-2 p-3 bg-gray-50 rounded-lg text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={syncEnabled}
              onChange={(e) => {
                const enabled = e.target.checked
                setSyncEnabled(enabled)
                handleSaveSettings(enabled, syncIntervalHours)
              }}
              disabled={savingSettings}
              className="rounded border-gray-300"
            />
            <span className="text-gray-700 font-medium">Auto-sync</span>
          </label>
          {syncEnabled && (
            <select
              value={syncIntervalHours}
              onChange={(e) => {
                const hours = parseInt(e.target.value, 10)
                setSyncIntervalHours(hours)
                handleSaveSettings(true, hours)
              }}
              disabled={savingSettings}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value={1}>Every hour</option>
              <option value={12}>Every 12 hours</option>
              <option value={24}>Daily</option>
            </select>
          )}
          {savingSettings && <span className="text-xs text-gray-400">Saving...</span>}
        </div>
      )}

      {error && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          Sync complete — <strong>{result.transactions_created} new transactions</strong> added
          {result.skipped_duplicate > 0 && `, ${result.skipped_duplicate} duplicates skipped`}
          {result.parse_failed > 0 && (
            <span className="text-amber-700">, {result.parse_failed} parse errors</span>
          )}
          {result.unmatched > 0 && `, ${result.unmatched} unrecognised emails`}
          <span className="block text-xs text-green-600 mt-1">
            {result.emails_fetched} emails fetched from Gmail
            {result.parsed_ok > 0 && ` · ${result.parsed_ok} parsed successfully`}
          </span>
        </div>
      )}
    </div>
  )
}
