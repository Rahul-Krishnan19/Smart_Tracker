import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { transactionsApi, analyticsApi } from '../services/api'
import CalendarModal from '../components/ui/CalendarModal'

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

const MO = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function todayISO() {
  const d = new Date(); const pad = n => n<10?'0'+n:''+n
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}
function daysAgoISO(n) {
  const d = new Date(); d.setDate(d.getDate()-n); const pad = x => x<10?'0'+x:''+x
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}
function fromISO(s) { const p=s.split('-'); return new Date(+p[0],+p[1]-1,+p[2]) }

function rangeLabel(start, end) {
  const t = todayISO()
  if (end === t) {
    for (const n of [7,30,90]) { if (start === daysAgoISO(n-1)) return 'Last '+n+' days' }
    const d = new Date(); d.setDate(1); const pad=x=>x<10?'0'+x:''+x
    const fom = d.getFullYear()+'-'+pad(d.getMonth()+1)+'-01'
    if (start === fom) return 'This month'
  }
  const a = fromISO(start), b = fromISO(end)
  return a.getDate()+' '+MO[a.getMonth()]+' – '+b.getDate()+' '+MO[b.getMonth()]
}

function formatINR(v) {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(v)
}

function AnimatedDonut({ segments, total, size = 190, strokeWidth = 26, centerContent }) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  let cumulative = 0

  return (
    <div style={{ position:'relative', width:size, height:size, margin:'0 auto 18px' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform:'rotate(-90deg)' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke="#1B212B"
          strokeWidth={strokeWidth}
        />
        <AnimatePresence>
          {segments.map((seg, i) => {
            if (!seg.amount) return null
            const pct = total ? seg.amount / total : 0
            const dash = pct * circumference
            const offset = (cumulative / total || 0) * circumference
            cumulative += seg.amount
            return (
              <motion.circle
                key={seg.name}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke={seg.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dash} ${circumference}`}
                strokeLinecap="butt"
                initial={{ strokeDashoffset: circumference, opacity: 0 }}
                animate={{ strokeDashoffset: -offset, opacity: 1 }}
                transition={{
                  strokeDashoffset: { duration: 0.9, delay: i * 0.08, ease: 'easeOut' },
                  opacity: { duration: 0.3, delay: i * 0.08 },
                }}
              />
            )
          })}
        </AnimatePresence>
      </svg>
      <div style={{ position:'absolute', inset:strokeWidth + 4, borderRadius:'50%', background:'#141921', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center' }}>
        {centerContent}
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const [dateStart, setDateStart] = useState(daysAgoISO(29))
  const [dateEnd, setDateEnd] = useState(todayISO())
  const [showCal, setShowCal] = useState(false)
  const [dim, setDim] = useState('category')
  const [summary, setSummary] = useState(null)
  const [trendData, setTrendData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchAll = useCallback(async (start, end) => {
    setLoading(true)
    try {
      const [sumRes, trendRes] = await Promise.all([
        transactionsApi.summary({ date_from: start, date_to: end }),
        analyticsApi.trend({ date_from: start, date_to: end, granularity: 'weekly' }).catch(() => ({ data: { trend: [] } })),
      ])
      setSummary(sumRes.data)
      setTrendData(trendRes.data.trend || [])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAll(dateStart, dateEnd) }, [dateStart, dateEnd, fetchAll])

  function applyRange(start, end) {
    setDateStart(start); setDateEnd(end); setShowCal(false)
  }

  // Build breakdown
  const breakdown = summary
    ? (dim === 'category' ? summary.category_breakdown || [] : summary.payment_breakdown || [])
        .map(row => ({
          name: dim === 'category' ? row.category : row.payment_method,
          amount: row.total,
          color: dim === 'category' ? (CATEGORY_COLORS[row.category] || '#8B95A1') : (METHOD_COLORS[row.payment_method] || '#8B95A1'),
        }))
        .sort((a, b) => b.amount - a.amount)
    : []

  const btot = breakdown.reduce((a, c) => a + c.amount, 0)
  const breakdownWithPct = breakdown.map(o => ({
    ...o,
    pct: btot ? ((o.amount / btot) * 100).toFixed(1) + '%' : '0%',
    pctNum: btot ? (o.amount / btot) * 100 : 0,
  }))

  // Trend bars
  const maxV = Math.max(1, ...trendData.map(b => b.amount || b.total || 0))
  const bars = trendData.slice(-8).map(b => {
    const v = b.amount || b.total || 0
    const labelRaw = b.period || b.date || ''
    let label = labelRaw
    if (labelRaw.length === 7) { const p = labelRaw.split('-'); label = MO[parseInt(p[1])-1] }
    else if (labelRaw.length === 10) { const d = fromISO(labelRaw); label = d.getDate()+' '+MO[d.getMonth()] }
    return { label, value: v, height: Math.max(3, v / maxV * 100) }
  })

  const segSel = { padding:'7px 13px', borderRadius:9, fontSize:12.5, fontWeight:700, cursor:'pointer', background:'#16B88A', color:'#06231B', border:'none', fontFamily:'inherit' }
  const segUn = { padding:'7px 13px', borderRadius:9, fontSize:12.5, fontWeight:600, cursor:'pointer', background:'transparent', color:'#8B95A1', border:'none', fontFamily:'inherit' }

  return (
    <div style={{ padding:'18px 16px 0' }}>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
        <div style={{ fontSize:20, fontWeight:800, color:'#EAEEF2' }}>Reports</div>
        <button onClick={() => setShowCal(true)} style={{ width:40, height:40, borderRadius:12, background:'#141921', border:'1px solid rgba(255,255,255,0.07)', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer' }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18"/><path d="M8 3v4M16 3v4"/></svg>
        </button>
      </div>

      {/* Range pill */}
      <button onClick={() => setShowCal(true)} style={{ display:'inline-flex', alignItems:'center', gap:8, padding:'8px 13px', borderRadius:999, background:'#141921', border:'1px solid rgba(255,255,255,0.08)', cursor:'pointer', marginBottom:16, fontFamily:'inherit' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#16B88A" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18"/><path d="M8 3v4M16 3v4"/></svg>
        <span style={{ fontSize:13, fontWeight:700, color:'#EAEEF2' }}>{rangeLabel(dateStart, dateEnd)}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6"/></svg>
      </button>

      {/* Spending trend */}
      <div style={{ background:'#141921', border:'1px solid rgba(255,255,255,0.06)', borderRadius:18, padding:'18px 16px' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <div style={{ fontSize:14, fontWeight:700, color:'#EAEEF2' }}>Spending trend</div>
          <div style={{ fontSize:12, color:'#8B95A1' }}>{rangeLabel(dateStart, dateEnd)}</div>
        </div>
        {bars.length > 0 ? (
          <div style={{ display:'flex', alignItems:'flex-end', gap:7, height:152, marginTop:20 }}>
            {bars.map((b, i) => (
              <div key={i} style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:9, height:'100%', justifyContent:'flex-end', minWidth:0 }}>
                <div style={{ width:'100%', display:'flex', alignItems:'flex-end', height:'100%' }}>
                  <div style={{ width:'100%', borderRadius:'6px 6px 2px 2px', background:'linear-gradient(180deg,#16B88A,#0E7C66)', height:b.height+'%', transition:'height .4s ease' }} />
                </div>
                <div style={{ fontSize:10, color:'#5C6671', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:'100%' }}>{b.label}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ height:152, marginTop:20, display:'flex', alignItems:'center', justifyContent:'center', color:'#5C6671', fontSize:13 }}>
            {loading ? 'Loading…' : 'No data'}
          </div>
        )}
      </div>

      {/* Breakdown section */}
      <div style={{ marginTop:18, display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div style={{ fontSize:15, fontWeight:700, color:'#EAEEF2' }}>Breakdown</div>
        <div style={{ display:'flex', background:'#10151C', border:'1px solid rgba(255,255,255,0.07)', borderRadius:11, padding:3, gap:2 }}>
          <button onClick={() => setDim('category')} style={dim === 'category' ? segSel : segUn}>Category</button>
          <button onClick={() => setDim('payment')} style={dim === 'payment' ? segSel : segUn}>Payment</button>
        </div>
      </div>

      <div style={{ marginTop:12, background:'#141921', border:'1px solid rgba(255,255,255,0.06)', borderRadius:18, padding:'22px 16px 18px' }}>
        {/* Donut */}
        <AnimatedDonut
          key={dim + dateStart + dateEnd}
          segments={breakdownWithPct}
          total={btot}
          centerContent={
            <>
              <div style={{ fontSize:10.5, color:'#8B95A1', textTransform:'uppercase', letterSpacing:'0.06em' }}>Total</div>
              <div style={{ fontSize:23, fontWeight:800, color:'#EAEEF2', marginTop:3, fontVariantNumeric:'tabular-nums' }}>{formatINR(btot)}</div>
            </>
          }
        />

        {/* Legend */}
        {breakdownWithPct.length === 0 && (
          <div style={{ textAlign:'center', padding:'14px 0', color:'#5C6671', fontSize:13 }}>No data for this period</div>
        )}
        {breakdownWithPct.map(o => (
          <div key={o.name} style={{ marginTop:15 }}>
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:7 }}>
              <div style={{ width:10, height:10, borderRadius:3, flexShrink:0, background:o.color }} />
              <div style={{ flex:1, fontSize:13.5, color:'#EAEEF2', fontWeight:600, minWidth:0, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{o.name}</div>
              <div style={{ fontSize:13, color:'#EAEEF2', fontWeight:700, fontVariantNumeric:'tabular-nums' }}>{formatINR(o.amount)}</div>
              <div style={{ fontSize:11, color:'#8B95A1', width:44, textAlign:'right' }}>{o.pct}</div>
            </div>
            <div style={{ height:6, borderRadius:999, background:'#1B212B', overflow:'hidden' }}>
              <div style={{ height:'100%', borderRadius:999, background:o.color, width:Math.max(2, o.pctNum)+'%' }} />
            </div>
          </div>
        ))}
      </div>

      {showCal && (
        <CalendarModal
          start={dateStart}
          end={dateEnd}
          onApply={applyRange}
          onClose={() => setShowCal(false)}
        />
      )}
    </div>
  )
}
