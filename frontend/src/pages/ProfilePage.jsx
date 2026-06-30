import { useAuth } from '../context/AuthContext'

export default function ProfilePage() {
  const { user, logout } = useAuth()
  const username = user?.username || 'User'
  const email = user?.email || ''
  const initials = username.slice(0, 2).toUpperCase()

  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
    : 'Jan 2025'

  return (
    <div style={{ padding:'18px 16px 0' }}>
      <div style={{ fontSize:20, fontWeight:800, color:'#EAEEF2', marginBottom:18 }}>Profile</div>

      {/* Avatar + name */}
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', textAlign:'center', padding:'10px 0 26px' }}>
        <div style={{ width:82, height:82, borderRadius:25, background:'linear-gradient(145deg,#16B88A,#0E7C66)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:29, fontWeight:800, color:'#06231B' }}>
          {initials}
        </div>
        <div style={{ fontSize:19, fontWeight:800, color:'#EAEEF2', marginTop:15 }}>{username}</div>
        {email && <div style={{ fontSize:13, color:'#8B95A1', marginTop:3 }}>{email}</div>}
      </div>

      {/* Info rows */}
      <div style={{ background:'#141921', border:'1px solid rgba(255,255,255,0.06)', borderRadius:16, overflow:'hidden' }}>
        <div style={{ display:'flex', alignItems:'center', padding:'16px 15px', borderBottom:'1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ flex:1, fontSize:14, color:'#8B95A1' }}>Member since</div>
          <div style={{ fontSize:14, color:'#EAEEF2', fontWeight:600 }}>{memberSince}</div>
        </div>
        <div style={{ display:'flex', alignItems:'center', padding:'16px 15px' }}>
          <div style={{ flex:1, fontSize:14, color:'#8B95A1' }}>Default currency</div>
          <div style={{ fontSize:14, color:'#EAEEF2', fontWeight:600 }}>₹ INR</div>
        </div>
      </div>

      {/* Logout */}
      <button
        onClick={logout}
        style={{ marginTop:18, width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:8, padding:15, borderRadius:14, border:'1px solid rgba(255,99,99,0.3)', color:'#FF7B7B', fontWeight:700, fontSize:14, cursor:'pointer', background:'rgba(255,99,99,0.06)', fontFamily:'inherit' }}
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FF7B7B" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>
        </svg>
        Log out
      </button>
    </div>
  )
}
