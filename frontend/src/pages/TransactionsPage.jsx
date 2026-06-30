import { useState, useEffect, useCallback } from 'react'
import { transactionsApi } from '../services/api'
import api from '../services/api'
import CalendarModal from '../components/ui/CalendarModal'
import GmailReconnectSheet from '../components/ui/GmailReconnectSheet'

const CATEGORY_COLORS = {
  'Food & Dining':     '#FF8A3D',
  'Groceries':         '#16B88A',
  'Travel':            '#34D399',
  'Entertainment':     '#EC4899',
  'Shopping':          '#7C5CFF',
  'Utilities':         '#F4B740',
  'Fuel':              '#F97316',
  'Healthcare':        '#22D3EE',
  'Education':         '#60A5FA',
  'Insurance':         '#A78BFA',
  'Investments':       '#4ADE80',
  'Financial Services':'#FB923C',
  'Subscriptions':     '#6366f1',
  'Transfers':         '#94A3B8',
  'Rent':              '#14b8a6',
  'Salary':            '#4ADE80',
  'Cashback & Rewards':'#FBBF24',
  'Others':            '#8B95A1',
}

const METHOD_COLORS = {
  'UPI': '#16B88A',
  'Credit Card': '#7C5CFF',
  'Debit Card': '#3B82F6',
  'Net Banking': '#F4B740',
  'Cash': '#8B95A1',
}

const WD = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
const MO = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function todayISO() {
  const d = new Date()
  const pad = n => n < 10 ? '0'+n : ''+n
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}
function daysAgoISO(n) {
  const d = new Date(); d.setDate(d.getDate() - n)
  const pad = x => x < 10 ? '0'+x : ''+x
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}
function fromISO(s) {
  const p = s.split('-'); return new Date(+p[0], +p[1]-1, +p[2])
}

function dayLabel(iso) {
  const t = todayISO()
  const y = daysAgoISO(1)
  if (iso === t) return 'Today'
  if (iso === y) return 'Yesterday'
  const d = fromISO(iso)
  return WD[d.getDay()]+', '+d.getDate()+' '+MO[d.getMonth()]+' '+d.getFullYear()
}

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:2 }).format(v)
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function groupTransactions(items) {
  const sorted = [...items].sort((a, b) => {
    const da = a.date || a.created_at || ''
    const db = b.date || b.created_at || ''
    return da < db ? 1 : da > db ? -1 : 0
  })
  const groups = []
  let cur = null
  for (const t of sorted) {
    const iso = (t.date || t.created_at || '').slice(0, 10)
    if (!cur || cur.date !== iso) {
      cur = { date: iso, label: dayLabel(iso), items: [], total: 0 }
      groups.push(cur)
    }
    cur.items.push(t)
    cur.total += parseFloat(t.amount)
  }
  return groups
}

function catInitial(cat) {
  if (!cat) return '?'
  if (cat === 'Food & Dining') return 'F'
  if (cat === 'Bills & Utilities' || cat === 'Utilities') return 'B'
  return cat[0].toUpperCase()
}

function TxRow({ t }) {
  const cat = t.category || 'Others'
  const color = CATEGORY_COLORS[cat] || '#8B95A1'
  const merchant = t.merchant_name || t.description || cat
  const sub = cat + (t.payment_method ? ' · ' + t.payment_method : '')
  return (
    <div style={{ display:'flex', alignItems:'center', gap:12, padding:'13px 14px', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
      <div style={{ width:38, height:38, borderRadius:11, display:'flex', alignItems:'center', justifyContent:'center', fontSize:14, fontWeight:800, color:'#06231B', flexShrink:0, background:color }}>
        {catInitial(cat)}
      </div>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ fontSize:14, fontWeight:600, color:'#EAEEF2', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{merchant}</div>
        <div style={{ fontSize:11.5, color:'#8B95A1', marginTop:2 }}>{sub}</div>
      </div>
      <div style={{ fontSize:14, fontWeight:700, color:'#EAEEF2', fontVariantNumeric:'tabular-nums' }}>−{formatINR(t.amount)}</div>
    </div>
  )
}

function TxGroup({ g }) {
  return (
    <div style={{ marginTop:16 }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:8, padding:'0 2px' }}>
        <div style={{ fontSize:12, color:'#8B95A1', fontWeight:600 }}>{g.label}</div>
        <div style={{ fontSize:12, color:'#5C6671', fontVariantNumeric:'tabular-nums' }}>{formatINR(g.total)}</div>
      </div>
      <div style={{ background:'#141921', border:'1px solid rgba(255,255,255,0.06)', borderRadius:16, overflow:'hidden' }}>
        {g.items.map((t, i) => <TxRow key={t.id || i} t={t} />)}
      </div>
    </div>
  )
}

export default function TransactionsPage({ refreshKey }) {
  const [dateStart, setDateStart] = useState(daysAgoISO(29))
  const [dateEnd, setDateEnd] = useState(todayISO())
  const [showCal, setShowCal] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [filterCat, setFilterCat] = useState('all')
  const [filterMethod, setFilterMethod] = useState('all')
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')
  const [showReconnect, setShowReconnect] = useState(false)
  const [reconnectMsg, setReconnectMsg] = useState('')
  const [connecting, setConnecting] = useState(false)

  const fetch = useCallback(async (start, end) => {
    setLoading(true)
    try {
      const [txRes, sumRes] = await Promise.all([
        transactionsApi.list({ date_from: start, date_to: end, page_size: 200 }),
        transactionsApi.summary({ date_from: start, date_to: end }),
      ])
      setItems(txRes.data.items || [])
      setSummary(sumRes.data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetch(dateStart, dateEnd) }, [dateStart, dateEnd, refreshKey, fetch])

  function applyRange(start, end) {
    setDateStart(start); setDateEnd(end); setShowCal(false)
  }

  async function handleSync() {
    setSyncing(true)
    setSyncMsg('')
    try {
      const res = await api.post('/gmail/sync?max_emails=200')
      setSyncMsg(`Synced — ${res.data.transactions_created} new transaction(s)`)
      fetch(dateStart, dateEnd)
      setSyncing(false)
      setTimeout(() => setSyncMsg(''), 3500)
    } catch (e) {
      setSyncing(false)
      if (e.response?.status === 400) {
        setReconnectMsg(e.response?.data?.detail || '')
        setShowReconnect(true)
      } else {
        setSyncMsg(e.response?.data?.detail || 'Sync failed. Please try again.')
        setTimeout(() => setSyncMsg(''), 3500)
      }
    }
  }

  async function handleConnectGmail() {
    setConnecting(true)
    try {
      const res = await api.get('/gmail/auth-url')
      window.location.href = res.data.auth_url
    } catch {
      setConnecting(false)
    }
  }

  // Compute top categories
  const catMap = {}
  items.forEach(t => { catMap[t.category] = (catMap[t.category] || 0) + parseFloat(t.amount) })
  const topCats = Object.entries(catMap)
    .map(([name, amount]) => ({ name, amount, color: CATEGORY_COLORS[name] || '#8B95A1', initial: catInitial(name) }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 5)

  const numDays = Math.max(1, Math.round((fromISO(dateEnd) - fromISO(dateStart)) / 86400000) + 1)
  const total = summary?.total_amount ?? items.reduce((a, t) => a + parseFloat(t.amount), 0)
  const txCount = summary?.transaction_count ?? items.length
  const avgPerDay = total / numDays

  const groups = groupTransactions(items)
  const recentGroups = groups.slice(0, 3).map(g => ({ ...g, items: g.items.slice(0, 4) }))
  const hasMore = groups.length > 3 || (groups[0] && groups[0].items.length > 4)

  // All transactions filtered
  const allItems = items.filter(t => {
    if (filterCat !== 'all' && t.category !== filterCat) return false
    if (filterMethod !== 'all' && t.payment_method !== filterMethod) return false
    return true
  })
  const allGroups = groupTransactions(allItems)
  const allTotal = allItems.reduce((a, t) => a + parseFloat(t.amount), 0)

  const allCats = [...new Set(items.map(t => t.category).filter(Boolean))]
  const allMethods = [...new Set(items.map(t => t.payment_method).filter(Boolean))]

  const fsel = { flexShrink:0, padding:'8px 14px', borderRadius:999, fontSize:12.5, fontWeight:600, cursor:'pointer', whiteSpace:'nowrap', background:'#16B88A', color:'#06231B', border:'1px solid #16B88A', fontFamily:'inherit' }
  const fun = { flexShrink:0, padding:'8px 14px', borderRadius:999, fontSize:12.5, fontWeight:600, cursor:'pointer', whiteSpace:'nowrap', background:'#141921', color:'#8B95A1', border:'1px solid rgba(255,255,255,0.08)', fontFamily:'inherit' }

  return (
    <div style={{ position:'relative', minHeight:'100vh', padding:'18px 16px 0' }}>
      {syncMsg && (
        <div style={{ position:'fixed', top:16, left:'50%', transform:'translateX(-50%)', background:'#1A212B', color:'#EAEEF2', fontSize:12.5, fontWeight:600, padding:'9px 16px', borderRadius:999, border:'1px solid rgba(255,255,255,0.1)', boxShadow:'0 8px 22px rgba(0,0,0,0.45)', zIndex:60, whiteSpace:'nowrap', maxWidth:'90%', overflow:'hidden', textOverflow:'ellipsis' }}>
          {syncMsg}
        </div>
      )}
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
        <div style={{ fontSize:18, fontWeight:800, color:'#EAEEF2' }}>{greeting()}</div>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <button onClick={handleSync} disabled={syncing} title="Sync emails" style={{ width:40, height:40, borderRadius:12, background:'#141921', border:'1px solid rgba(255,255,255,0.07)', display:'flex', alignItems:'center', justifyContent:'center', cursor: syncing ? 'default' : 'pointer', opacity: syncing ? 0.6 : 1 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={syncing ? { animation:'spin 1s linear infinite' } : undefined}>
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
          <button onClick={() => setShowCal(true)} style={{ width:40, height:40, borderRadius:12, background:'#141921', border:'1px solid rgba(255,255,255,0.07)', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer' }}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18"/><path d="M8 3v4M16 3v4"/></svg>
          </button>
        </div>
      </div>

      {/* Stats card */}
      <div style={{ borderRadius:20, padding:'22px 20px', background:'linear-gradient(160deg,#1A212B,#10151C)', border:'1px solid rgba(255,255,255,0.06)', position:'relative', overflow:'hidden' }}>
        <div style={{ position:'absolute', top:-40, right:-30, width:140, height:140, borderRadius:'50%', background:'radial-gradient(circle,rgba(22,184,138,0.22),transparent 70%)' }} />
        <div style={{ fontSize:12, color:'#8B95A1', fontWeight:600, letterSpacing:'0.05em', textTransform:'uppercase' }}>Total expenses</div>
        <div style={{ fontSize:38, fontWeight:800, color:'#EAEEF2', marginTop:6, letterSpacing:'-0.02em', fontVariantNumeric:'tabular-nums' }}>{formatINR(total)}</div>
        <div style={{ display:'flex', alignItems:'center', gap:12, marginTop:10, fontSize:12.5, color:'#8B95A1' }}>
          <span>{txCount} transactions</span>
          <span style={{ color:'#3A434E' }}>•</span>
          <span>avg {formatINR(avgPerDay)}/day</span>
        </div>
      </div>

      {/* AI Insights banner */}
      <div style={{ marginTop:12, display:'flex', alignItems:'center', gap:12, padding:'14px 16px', borderRadius:16, background:'linear-gradient(120deg,#10261F,#0E1A23)', border:'1px solid rgba(22,184,138,0.28)', cursor:'pointer' }}>
        <div style={{ width:38, height:38, borderRadius:11, background:'rgba(22,184,138,0.16)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="1.6" strokeLinejoin="round"><path d="M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5l4.6-1.9z"/></svg>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:13.5, color:'#EAEEF2', fontWeight:700 }}>Your insights are ready</div>
          <div style={{ fontSize:11.5, color:'#8B95A1', marginTop:1 }}>Tap to see where your money goes</div>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6"/></svg>
      </div>

      {/* Top categories */}
      {topCats.length > 0 && (
        <>
          <div style={{ marginTop:24, marginBottom:12, fontSize:15, fontWeight:700, color:'#EAEEF2' }}>Top categories</div>
          <div style={{ display:'flex', gap:10, overflowX:'auto', paddingBottom:4 }}>
            {topCats.map(c => (
              <div key={c.name} style={{ flexShrink:0, minWidth:130, padding:14, borderRadius:16, background:'#141921', border:'1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ width:30, height:30, borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:800, color:'#06231B', background:c.color }}>{c.initial}</div>
                <div style={{ fontSize:12, color:'#8B95A1', marginTop:11, whiteSpace:'nowrap' }}>{c.name}</div>
                <div style={{ fontSize:15, fontWeight:700, color:'#EAEEF2', marginTop:2, fontVariantNumeric:'tabular-nums' }}>{formatINR(c.amount)}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Transactions heading */}
      <div style={{ marginTop:26, display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:4 }}>
        <div style={{ fontSize:15, fontWeight:700, color:'#EAEEF2' }}>Transactions</div>
        {hasMore && (
          <button onClick={() => setShowAll(true)} style={{ display:'flex', alignItems:'center', gap:3, fontSize:13, color:'#16B88A', fontWeight:700, cursor:'pointer', background:'none', border:'none', fontFamily:'inherit' }}>
            View all
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6"/></svg>
          </button>
        )}
      </div>

      {loading && <div style={{ textAlign:'center', padding:'40px 0', color:'#5C6671', fontSize:13 }}>Loading…</div>}
      {!loading && items.length === 0 && <div style={{ textAlign:'center', padding:'40px 0', color:'#5C6671', fontSize:13 }}>No expenses in this period</div>}
      {!loading && recentGroups.map(g => <TxGroup key={g.date} g={g} />)}

      {/* All Transactions overlay */}
      {showAll && (
        <div style={{ position:'fixed', inset:0, background:'#0B0E13', zIndex:45, display:'flex', flexDirection:'column', animation:'slideIn .26s ease', maxWidth:430, margin:'0 auto' }}>
          <div style={{ display:'flex', alignItems:'center', gap:12, padding:'18px 16px 14px' }}>
            <button onClick={() => setShowAll(false)} style={{ width:38, height:38, borderRadius:11, background:'#141921', border:'1px solid rgba(255,255,255,0.07)', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EAEEF2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6"/></svg>
            </button>
            <div style={{ fontSize:18, fontWeight:800, color:'#EAEEF2' }}>All transactions</div>
          </div>

          {/* Cat filters */}
          <div style={{ padding:'6px 16px 8px' }}>
            <div style={{ display:'flex', gap:8, overflowX:'auto', paddingBottom:9 }}>
              <button onClick={() => setFilterCat('all')} style={filterCat === 'all' ? fsel : fun}>All categories</button>
              {allCats.map(c => <button key={c} onClick={() => setFilterCat(c)} style={filterCat === c ? fsel : fun}>{c}</button>)}
            </div>
            <div style={{ display:'flex', gap:8, overflowX:'auto' }}>
              <button onClick={() => setFilterMethod('all')} style={filterMethod === 'all' ? fsel : fun}>All methods</button>
              {allMethods.map(m => <button key={m} onClick={() => setFilterMethod(m)} style={filterMethod === m ? fsel : fun}>{m}</button>)}
            </div>
          </div>

          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 16px', borderTop:'1px solid rgba(255,255,255,0.05)', borderBottom:'1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ fontSize:12.5, color:'#8B95A1' }}>{allItems.length} transactions</span>
            <span style={{ fontSize:13, fontWeight:700, color:'#EAEEF2', fontVariantNumeric:'tabular-nums' }}>{formatINR(allTotal)}</span>
          </div>

          <div style={{ flex:1, overflowY:'auto', padding:'4px 16px 24px' }}>
            {allItems.length === 0 && <div style={{ textAlign:'center', padding:'50px 0', color:'#5C6671', fontSize:13 }}>No transactions match these filters</div>}
            {allGroups.map(g => <TxGroup key={g.date} g={g} />)}
          </div>
        </div>
      )}

      {/* Calendar modal */}
      {showCal && (
        <CalendarModal
          start={dateStart}
          end={dateEnd}
          onApply={applyRange}
          onClose={() => setShowCal(false)}
        />
      )}

      {/* Gmail reconnect sheet */}
      {showReconnect && (
        <GmailReconnectSheet
          message={reconnectMsg}
          connecting={connecting}
          onConnect={handleConnectGmail}
          onClose={() => setShowReconnect(false)}
        />
      )}
    </div>
  )
}
