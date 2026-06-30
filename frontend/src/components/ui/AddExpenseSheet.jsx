import { useState } from 'react'
import { transactionsApi } from '../../services/api'

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
  'Investments':       '#34D399',
  'Financial Services':'#FB923C',
  'Subscriptions':     '#6366f1',
  'Transfers':         '#94A3B8',
  'Rent':              '#14b8a6',
  'Salary':            '#4ADE80',
  'Cashback & Rewards':'#FBBF24',
  'Others':            '#8B95A1',
}

const CATEGORIES = [
  'Food & Dining', 'Groceries', 'Travel', 'Entertainment', 'Shopping',
  'Utilities', 'Fuel', 'Healthcare', 'Education', 'Insurance',
  'Investments', 'Financial Services', 'Subscriptions', 'Transfers',
  'Rent', 'Salary', 'Cashback & Rewards', 'Others',
]
const METHODS = ['UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'Cash']

function todayISO() {
  const d = new Date()
  const pad = n => n < 10 ? '0'+n : ''+n
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())
}

export default function AddExpenseSheet({ onClose, onAdded }) {
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('Food & Dining')
  const [method, setMethod] = useState('UPI')
  const [merchant, setMerchant] = useState('')
  const [date, setDate] = useState(todayISO())
  const [loading, setLoading] = useState(false)

  const canSubmit = parseFloat(amount) > 0

  async function submit() {
    if (!canSubmit) return
    setLoading(true)
    try {
      await transactionsApi.create({
        amount: parseFloat(amount),
        category,
        payment_method: method,
        merchant_name: merchant || undefined,
        date,
        description: merchant || category,
      })
      onAdded && onAdded()
      onClose()
    } catch {
      // ignore, user can retry
    } finally {
      setLoading(false)
    }
  }

  const selChip = { padding:'9px 13px', borderRadius:11, fontSize:12.5, fontWeight:600, cursor:'pointer', background:'rgba(22,184,138,0.16)', border:'1px solid #16B88A', color:'#16B88A', fontFamily:'inherit' }
  const unChip = { padding:'9px 13px', borderRadius:11, fontSize:12.5, fontWeight:600, cursor:'pointer', background:'#181E27', border:'1px solid rgba(255,255,255,0.07)', color:'#8B95A1', fontFamily:'inherit' }

  return (
    <div style={{ position:'fixed', inset:0, zIndex:50 }}>
      <div onClick={onClose} style={{ position:'absolute', inset:0, background:'rgba(0,0,0,0.6)', animation:'fadeIn .2s ease' }} />
      <div style={{ position:'absolute', left:0, right:0, bottom:0, background:'#10151C', borderRadius:'24px 24px 0 0', borderTop:'1px solid rgba(255,255,255,0.08)', padding:'18px 18px 26px', animation:'sheetUp .3s cubic-bezier(.2,.85,.25,1)', maxHeight:'90%', overflowY:'auto', maxWidth:430, margin:'0 auto' }}>
        <div style={{ width:38, height:4, borderRadius:99, background:'#2A323D', margin:'0 auto 16px' }} />
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:18 }}>
          <div style={{ fontSize:17, fontWeight:800, color:'#EAEEF2' }}>Add expense</div>
          <button onClick={onClose} style={{ width:30, height:30, borderRadius:9, background:'#1B212B', display:'flex', alignItems:'center', justifyContent:'center', border:'none', cursor:'pointer' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>

        {/* Amount */}
        <div style={{ textAlign:'center', marginBottom:22 }}>
          <div style={{ fontSize:12, color:'#8B95A1', marginBottom:8 }}>Amount</div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:4 }}>
            <span style={{ fontSize:30, fontWeight:800, color:'#5C6671' }}>₹</span>
            <input
              value={amount}
              onChange={e => setAmount(e.target.value)}
              inputMode="decimal"
              placeholder="0"
              style={{ width:170, background:'transparent', border:'none', outline:'none', fontSize:38, fontWeight:800, color:'#EAEEF2', textAlign:'center', fontFamily:'inherit' }}
            />
          </div>
        </div>

        {/* Category */}
        <div style={{ fontSize:12, color:'#8B95A1', marginBottom:10, fontWeight:600 }}>Category</div>
        <div style={{ display:'flex', flexWrap:'wrap', gap:8, marginBottom:20 }}>
          {CATEGORIES.map(c => (
            <button key={c} onClick={() => setCategory(c)} style={category === c ? selChip : unChip}>{c}</button>
          ))}
        </div>

        {/* Payment method */}
        <div style={{ fontSize:12, color:'#8B95A1', marginBottom:10, fontWeight:600 }}>Payment method</div>
        <div style={{ display:'flex', flexWrap:'wrap', gap:8, marginBottom:20 }}>
          {METHODS.map(m => (
            <button key={m} onClick={() => setMethod(m)} style={method === m ? selChip : unChip}>{m}</button>
          ))}
        </div>

        {/* Merchant */}
        <input
          value={merchant}
          onChange={e => setMerchant(e.target.value)}
          placeholder="Merchant (optional)"
          style={{ width:'100%', background:'#141921', border:'1px solid rgba(255,255,255,0.08)', color:'#EAEEF2', borderRadius:12, padding:'13px 14px', fontSize:14, fontFamily:'inherit', marginBottom:12, outline:'none' }}
        />

        {/* Date */}
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          style={{ width:'100%', background:'#141921', border:'1px solid rgba(255,255,255,0.08)', color:'#EAEEF2', borderRadius:12, padding:'13px 14px', fontSize:14, fontFamily:'inherit', marginBottom:20, outline:'none', colorScheme:'dark' }}
        />

        {/* Submit */}
        <button
          onClick={submit}
          disabled={!canSubmit || loading}
          style={{ width:'100%', textAlign:'center', padding:15, borderRadius:14, fontWeight:800, fontSize:15, cursor: canSubmit ? 'pointer' : 'default', background: canSubmit ? '#16B88A' : '#1B212B', color: canSubmit ? '#06231B' : '#5C6671', border:'none', fontFamily:'inherit' }}
        >
          {loading ? 'Adding…' : 'Add expense'}
        </button>
      </div>
    </div>
  )
}
