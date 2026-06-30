export default function GmailReconnectSheet({ message, onConnect, onClose, connecting }) {
  return (
    <div style={{ position:'fixed', inset:0, zIndex:50 }}>
      <div onClick={onClose} style={{ position:'absolute', inset:0, background:'rgba(0,0,0,0.6)', animation:'fadeIn .2s ease' }} />
      <div style={{ position:'absolute', left:0, right:0, bottom:0, background:'#10151C', borderRadius:'24px 24px 0 0', borderTop:'1px solid rgba(255,255,255,0.08)', padding:'18px 18px 26px', animation:'sheetUp .3s cubic-bezier(.2,.85,.25,1)', maxWidth:430, margin:'0 auto' }}>
        <div style={{ width:38, height:4, borderRadius:99, background:'#2A323D', margin:'0 auto 16px' }} />
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
          <div style={{ fontSize:17, fontWeight:800, color:'#EAEEF2' }}>Gmail connection expired</div>
          <button onClick={onClose} style={{ width:30, height:30, borderRadius:9, background:'#1B212B', display:'flex', alignItems:'center', justifyContent:'center', border:'none', cursor:'pointer' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8B95A1" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>

        <div style={{ display:'flex', alignItems:'center', justifyContent:'center', width:54, height:54, borderRadius:16, background:'rgba(255,99,99,0.1)', margin:'4px auto 16px' }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FF7B7B" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5"/>
          </svg>
        </div>

        <div style={{ fontSize:13.5, color:'#8B95A1', textAlign:'center', lineHeight:1.5, padding:'0 8px', marginBottom:22 }}>
          {message || 'Your Gmail connection has expired. We need you to reconnect your Gmail account to keep syncing transactions automatically.'}
        </div>

        <button
          onClick={onConnect}
          disabled={connecting}
          style={{ width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:8, textAlign:'center', padding:15, borderRadius:14, fontWeight:800, fontSize:15, cursor: connecting ? 'default' : 'pointer', background:'#16B88A', color:'#06231B', border:'none', fontFamily:'inherit', opacity: connecting ? 0.7 : 1 }}
        >
          {connecting ? 'Opening Google…' : 'Connect Gmail'}
        </button>
      </div>
    </div>
  )
}
