import { useState } from 'react'

const WD = ['S','M','T','W','T','F','S']
const MO = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const MOF = ['January','February','March','April','May','June','July','August','September','October','November','December']

function toISO(d) {
  const pad = n => n < 10 ? '0'+n : ''+n
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}
function fromISO(s) {
  const p = s.split('-')
  return new Date(+p[0], +p[1]-1, +p[2])
}
function addDays(d, n) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()+n)
}

export default function CalendarModal({ start, end, onApply, onClose }) {
  const TODAY = new Date()
  const nowISO = toISO(TODAY)

  const initMonth = start ? fromISO(start) : TODAY
  const [calMonth, setCalMonth] = useState({ y: initMonth.getFullYear(), m: initMonth.getMonth() })
  const [calStart, setCalStart] = useState(start || null)
  const [calEnd, setCalEnd] = useState(end || null)

  function pickDay(iso) {
    if (!calStart || (calStart && calEnd)) {
      setCalStart(iso); setCalEnd(null)
    } else {
      if (iso >= calStart) setCalEnd(iso)
      else { setCalStart(iso); setCalEnd(null) }
    }
  }

  function applyPreset(kind) {
    let s
    if (kind === 'month') s = toISO(new Date(TODAY.getFullYear(), TODAY.getMonth(), 1))
    else s = toISO(addDays(TODAY, -(kind - 1)))
    setCalStart(s); setCalEnd(nowISO)
    onApply(s, nowISO)
  }

  function apply() {
    if (!calStart) return
    onApply(calStart, calEnd || calStart)
  }

  const { y: cy, m: cm } = calMonth
  const firstW = new Date(cy, cm, 1).getDay()
  const daysInMonth = new Date(cy, cm+1, 0).getDate()
  const canNext = (cy*12+cm) < (TODAY.getFullYear()*12+TODAY.getMonth())

  const cells = []
  for (let i = 0; i < firstW; i++) cells.push({ key:'b'+i, empty: true })
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = toISO(new Date(cy, cm, d))
    const future = iso > nowISO
    const isS = iso === calStart, isE = iso === calEnd
    const inR = calStart && calEnd && iso > calStart && iso < calEnd
    let style = { height:40, display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, borderRadius:11, fontWeight:600 }
    if (future) style = { ...style, color:'#3A434E', cursor:'default' }
    else if (isS || isE) style = { ...style, background:'#16B88A', color:'#06231B', cursor:'pointer' }
    else if (inR) style = { ...style, background:'rgba(22,184,138,0.16)', color:'#EAEEF2', cursor:'pointer' }
    else style = { ...style, color:'#EAEEF2', cursor:'pointer' }
    cells.push({ key:'d'+d, label:''+d, style, onClick: future ? null : () => pickDay(iso) })
  }

  let rangeText = 'Select start date'
  if (calStart && calEnd) {
    const a = fromISO(calStart), b = fromISO(calEnd)
    rangeText = a.getDate()+' '+MO[a.getMonth()]+' – '+b.getDate()+' '+MO[b.getMonth()]
  } else if (calStart) {
    const a = fromISO(calStart)
    rangeText = a.getDate()+' '+MO[a.getMonth()]+' – select end date'
  }

  const applyActive = !!calStart

  return (
    <div style={{ position:'fixed', inset:0, zIndex:50 }}>
      <div onClick={onClose} style={{ position:'absolute', inset:0, background:'rgba(0,0,0,0.6)', animation:'fadeIn .2s ease' }} />
      <div style={{ position:'absolute', left:0, right:0, bottom:0, background:'#10151C', borderRadius:'24px 24px 0 0', borderTop:'1px solid rgba(255,255,255,0.08)', padding:'18px 18px 26px', animation:'sheetUp .3s cubic-bezier(.2,.85,.25,1)', maxWidth:430, margin:'0 auto' }}>
        <div style={{ width:38, height:4, borderRadius:99, background:'#2A323D', margin:'0 auto 16px' }} />
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
          <div style={{ fontSize:17, fontWeight:800, color:'#EAEEF2' }}>Select date range</div>
          <button onClick={onClose} style={{ width:30, height:30, borderRadius:9, background:'#1B212B', display:'flex', alignItems:'center', justifyContent:'center', border:'none', cursor:'pointer' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>
        <div style={{ display:'flex', gap:8, marginBottom:18 }}>
          {[['Last 7 days', () => applyPreset(7)], ['Last 30 days', () => applyPreset(30)], ['This month', () => applyPreset('month')]].map(([label, fn]) => (
            <button key={label} onClick={fn} style={{ flex:1, textAlign:'center', padding:'9px', borderRadius:11, background:'#181E27', border:'1px solid rgba(255,255,255,0.07)', color:'#C2CAD3', fontSize:12.5, fontWeight:600, cursor:'pointer', fontFamily:'inherit' }}>{label}</button>
          ))}
        </div>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
          <button onClick={() => { const idx = cy*12+cm-1; setCalMonth({ y: Math.floor(idx/12), m: ((idx%12)+12)%12 }) }} style={{ width:34, height:34, borderRadius:10, background:'#181E27', display:'flex', alignItems:'center', justifyContent:'center', border:'none', cursor:'pointer' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6"/></svg>
          </button>
          <div style={{ fontSize:14.5, fontWeight:700, color:'#EAEEF2' }}>{MOF[cm]} {cy}</div>
          <button onClick={() => { if (canNext) { const idx = cy*12+cm+1; setCalMonth({ y: Math.floor(idx/12), m: idx%12 }) } }} style={{ width:34, height:34, borderRadius:10, background:'#181E27', display:'flex', alignItems:'center', justifyContent:'center', border:'none', cursor: canNext ? 'pointer' : 'default', opacity: canNext ? 1 : 0.3 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6"/></svg>
          </button>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(7,1fr)', gap:2, marginBottom:4 }}>
          {WD.map((d, i) => (
            <div key={i} style={{ height:28, display:'flex', alignItems:'center', justifyContent:'center', fontSize:11, color:'#5C6671', fontWeight:600 }}>{d}</div>
          ))}
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(7,1fr)', gap:2 }}>
          {cells.map(cell => cell.empty
            ? <div key={cell.key} style={{ height:40 }} />
            : <div key={cell.key} style={cell.style} onClick={cell.onClick}>{cell.label}</div>
          )}
        </div>
        <div style={{ textAlign:'center', margin:'18px 0 16px', fontSize:13, color:'#8B95A1' }}>{rangeText}</div>
        <button onClick={apply} disabled={!applyActive} style={{ width:'100%', textAlign:'center', padding:15, borderRadius:14, fontWeight:800, fontSize:15, cursor: applyActive ? 'pointer' : 'default', background: applyActive ? '#16B88A' : '#1B212B', color: applyActive ? '#06231B' : '#5C6671', border:'none', fontFamily:'inherit', pointerEvents: applyActive ? 'auto' : 'none' }}>Apply</button>
      </div>
    </div>
  )
}
