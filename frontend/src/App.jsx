import { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { FiltersProvider } from './context/FiltersContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginForm from './components/auth/LoginForm'
import RegisterForm from './components/auth/RegisterForm'
import TransactionsPage from './pages/TransactionsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import GmailCallbackPage from './pages/GmailCallbackPage'
import InsightsPage from './pages/InsightsPage'

const NavIcon = {
  Transactions: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 6h18M3 14h12M3 18h8" />
    </svg>
  ),
  Analytics: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 19V9l6-6 6 6 6-6v16" />
    </svg>
  ),
  Insights: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  ),
}

function Sidebar({ onClose }) {
  const { user, logout } = useAuth()
  const initial = user?.username?.[0]?.toUpperCase() || '?'

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
      isActive
        ? 'bg-emerald-500/20 text-emerald-400'
        : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
    }`

  return (
    <aside className="flex flex-col h-full bg-[#0d1117] w-64 py-6 px-4 flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-3 mb-8">
        <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white font-bold text-sm" style={{ fontFamily: 'Syne, sans-serif' }}>ST</span>
        </div>
        <span className="text-white font-bold text-base" style={{ fontFamily: 'Syne, sans-serif' }}>Smart Tracker</span>
      </div>

      {/* Nav section label */}
      <p className="section-label text-slate-600 px-3 mb-2">Menu</p>

      {/* Nav links */}
      <nav className="flex flex-col gap-1 flex-1">
        <NavLink to="/transactions" className={linkClass} onClick={onClose}>
          {NavIcon.Transactions}
          <span style={{ fontFamily: 'Syne, sans-serif' }}>Transactions</span>
        </NavLink>
        <NavLink to="/analytics" className={linkClass} onClick={onClose}>
          {NavIcon.Analytics}
          <span style={{ fontFamily: 'Syne, sans-serif' }}>Analytics</span>
        </NavLink>
        <NavLink to="/insights" className={linkClass} onClick={onClose}>
          {NavIcon.Insights}
          <span style={{ fontFamily: 'Syne, sans-serif' }}>Insights</span>
        </NavLink>
      </nav>

      {/* User section */}
      <div className="border-t border-white/10 pt-4 mt-4">
        <div className="flex items-center gap-3 px-3">
          <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
            <span className="text-emerald-400 text-sm font-bold">{initial}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-slate-200 text-sm font-medium truncate" style={{ fontFamily: 'Syne, sans-serif' }}>{user?.username}</p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="text-slate-500 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-white/5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}

function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">
        <Sidebar onClose={() => {}} />
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative z-50 h-full">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden bg-[#0d1117] border-b border-white/10 h-14 flex items-center justify-between px-4 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-slate-400 hover:text-slate-200 transition-colors p-1"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-emerald-500 flex items-center justify-center">
              <span className="text-white font-bold text-xs" style={{ fontFamily: 'Syne, sans-serif' }}>ST</span>
            </div>
            <span className="text-white font-bold text-sm" style={{ fontFamily: 'Syne, sans-serif' }}>Smart Tracker</span>
          </div>
          <div className="w-8" />
        </header>

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto bg-slate-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/transactions" element={<ProtectedRoute><Layout><TransactionsPage /></Layout></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><Layout><AnalyticsPage /></Layout></ProtectedRoute>} />
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
