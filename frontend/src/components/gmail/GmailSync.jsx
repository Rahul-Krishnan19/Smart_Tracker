import { useState, useEffect } from 'react'
import api from '../../services/api'
import { gmailSourcesApi } from '../../services/api'

function formatIST(isoString) {
  if (!isoString) return null
  return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
}

function SourcesPanel() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [newBank, setNewBank] = useState('')
  const [newPattern, setNewPattern] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    gmailSourcesApi.list()
      .then(r => setSources(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleToggle(source) {
    const updated = !source.enabled
    setSources(prev => prev.map(s => s.id === source.id ? { ...s, enabled: updated } : s))
    try {
      await gmailSourcesApi.toggle(source.id, updated)
    } catch {
      setSources(prev => prev.map(s => s.id === source.id ? { ...s, enabled: source.enabled } : s))
    }
  }

  async function handleAdd() {
    const bank = newBank.trim()
    const pattern = newPattern.trim().toLowerCase()
    if (!bank || !pattern) return
    if (!window.confirm(`Add "${pattern}" as a mail source for ${bank}? Emails from this sender will be fetched on next sync.`)) return
    setAdding(true)
    setError('')
    try {
      const res = await gmailSourcesApi.add({ bank_name: bank, sender_pattern: pattern })
      setSources(prev => [...prev, res.data])
      setNewBank('')
      setNewPattern('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to add source.')
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(source) {
    if (!window.confirm(`Remove ${source.bank_name} (${source.sender_pattern})? Emails from this sender will no longer be synced.`)) return
    try {
      await gmailSourcesApi.remove(source.id)
      setSources(prev => prev.filter(s => s.id !== source.id))
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to remove source.')
    }
  }

  if (loading) return <p className="text-xs text-gray-400 py-1">Loading sources…</p>

  return (
    <div className="mt-2 border border-gray-200 rounded-lg overflow-hidden text-sm">
      <div className="divide-y divide-gray-100">
        {sources.map(source => (
          <div key={source.id} className="flex items-center gap-3 px-3 py-2 bg-white hover:bg-gray-50">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={source.enabled}
                onChange={() => handleToggle(source)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 peer-checked:bg-blue-500 rounded-full transition-colors
                after:content-[''] after:absolute after:top-0.5 after:left-0.5
                after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all
                peer-checked:after:translate-x-4" />
            </label>
            <span className={`flex-1 ${source.enabled ? 'text-gray-800' : 'text-gray-400'}`}>
              <span className="font-medium">{source.bank_name}</span>
              <span className="text-gray-400 mx-1">—</span>
              <span className="font-mono text-xs">{source.sender_pattern}</span>
            </span>
            {!source.is_builtin && (
              <button
                onClick={() => handleDelete(source)}
                className="text-gray-300 hover:text-red-400 transition-colors text-xs px-1"
                title="Remove source"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add new source row */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-t border-gray-200">
        <input
          type="text"
          value={newBank}
          onChange={e => setNewBank(e.target.value)}
          placeholder="Bank name"
          className="flex-1 text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        <input
          type="text"
          value={newPattern}
          onChange={e => setNewPattern(e.target.value)}
          placeholder="sender domain or email"
          className="flex-1 text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-400"
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
        />
        <button
          onClick={handleAdd}
          disabled={adding || !newBank.trim() || !newPattern.trim()}
          className="text-xs px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {adding ? '…' : 'Add'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-600 px-3 py-1 bg-red-50">{error}</p>
      )}
    </div>
  )
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
  const [showSources, setShowSources] = useState(false)

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
      const res = await api.post('/gmail/sync?max_emails=200')
      setSyncResult(res.data)
      if (res.data.transactions_created > 0) onSyncComplete?.()
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
      setShowSources(false)
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

      {connected && (
        <div>
          <button
            onClick={() => setShowSources(prev => !prev)}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            {showSources ? '▲ Hide sources' : '▼ Manage sources'}
          </button>
          {showSources && <SourcesPanel />}
        </div>
      )}
    </div>
  )
}
