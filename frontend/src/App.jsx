import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { FiltersProvider } from './context/FiltersContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginForm from './components/auth/LoginForm'
import RegisterForm from './components/auth/RegisterForm'
import TransactionsPage from './pages/TransactionsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import GmailCallbackPage from './pages/GmailCallbackPage'
import InsightsPage from './pages/InsightsPage'
import ProfilePage from './pages/ProfilePage'
import AddExpenseSheet from './components/ui/AddExpenseSheet'

const HomeIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#16B88A' : '#5C6671'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 10.5 12 4l9 6.5"/><path d="M5 9.7V20h14V9.7"/>
  </svg>
)
const ReportsIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#16B88A' : '#5C6671'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 20h16"/><path d="M7 20v-7"/><path d="M12 20V6"/><path d="M17 20v-4"/>
  </svg>
)
const ProfileIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#16B88A' : '#5C6671'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="4"/><path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6"/>
  </svg>
)

function BottomNav({ onAddClick }) {
  const loc = useLocation()
  const isHome = loc.pathname === '/transactions'
  const isReports = loc.pathname === '/analytics'
  const isProfile = loc.pathname === '/profile'

  return (
    <>
      {/* Bottom nav bar */}
      <div style={{ position:'fixed', left:0, right:0, bottom:0, height:64, background:'rgba(11,14,19,0.97)', backdropFilter:'blur(16px)', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', alignItems:'center', zIndex:20, maxWidth:430, margin:'0 auto' }}>
        <NavLink to="/transactions" style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:5, textDecoration:'none' }}>
          <HomeIcon active={isHome} />
          <span style={{ fontSize:10, fontWeight:600, color: isHome ? '#16B88A' : '#5C6671' }}>Home</span>
        </NavLink>
        <NavLink to="/analytics" style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:5, textDecoration:'none' }}>
          <ReportsIcon active={isReports} />
          <span style={{ fontSize:10, fontWeight:600, color: isReports ? '#16B88A' : '#5C6671' }}>Reports</span>
        </NavLink>
        <NavLink to="/profile" style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:5, textDecoration:'none' }}>
          <ProfileIcon active={isProfile} />
          <span style={{ fontSize:10, fontWeight:600, color: isProfile ? '#16B88A' : '#5C6671' }}>Profile</span>
        </NavLink>
      </div>

      {/* Floating add button */}
      <button
        onClick={onAddClick}
        style={{ position:'fixed', left:'50%', bottom:74, transform:'translateX(-50%)', width:58, height:58, borderRadius:19, background:'linear-gradient(145deg,#16B88A,#0E7C66)', boxShadow:'0 10px 28px rgba(22,184,138,0.5)', display:'flex', alignItems:'center', justifyContent:'center', border:'4px solid #0B0E13', cursor:'pointer', zIndex:30 }}
        aria-label="Add expense"
      >
        <svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="#06231B" strokeWidth="2.6" strokeLinecap="round">
          <path d="M12 5v14M5 12h14"/>
        </svg>
      </button>
    </>
  )
}

function Layout({ children }) {
  const [showAdd, setShowAdd] = useState(false)
  const [flash, setFlash] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  const handleAdded = useCallback(() => {
    setFlash('Expense added')
    setRefreshKey(k => k + 1)
    setTimeout(() => setFlash(''), 2200)
  }, [])

  return (
    <div style={{ minHeight:'100vh', width:'100%', background:'#05070A', display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ position:'relative', width:'100%', maxWidth:430, minHeight:'100vh', background:'#0B0E13', overflow:'hidden' }}>
        {/* Flash toast */}
        {flash && (
          <div style={{ position:'fixed', top:16, left:'50%', transform:'translateX(-50%)', background:'#16B88A', color:'#06231B', fontSize:13, fontWeight:700, padding:'9px 18px', borderRadius:999, boxShadow:'0 8px 22px rgba(0,0,0,0.45)', zIndex:60, animation:'fadeIn .2s ease', whiteSpace:'nowrap' }}>
            {flash}
          </div>
        )}

        {/* Page content */}
        <div style={{ overflowY:'auto', paddingBottom:132, minHeight:'100vh' }}>
          {typeof children === 'function' ? children({ refreshKey }) : children}
        </div>

        <BottomNav onAddClick={() => setShowAdd(true)} />

        {showAdd && (
          <AddExpenseSheet onClose={() => setShowAdd(false)} onAdded={handleAdded} />
        )}
      </div>
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/transactions" element={
        <ProtectedRoute>
          <Layout>{({ refreshKey }) => <TransactionsPage refreshKey={refreshKey} />}</Layout>
        </ProtectedRoute>
      } />
      <Route path="/analytics" element={
        <ProtectedRoute>
          <Layout><AnalyticsPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/profile" element={
        <ProtectedRoute>
          <Layout><ProfilePage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/auth/gmail/callback" element={<ProtectedRoute><GmailCallbackPage /></ProtectedRoute>} />
      <Route path="/insights" element={<ProtectedRoute><Layout><InsightsPage /></Layout></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/transactions" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <FiltersProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </FiltersProvider>
    </BrowserRouter>
  )
}
