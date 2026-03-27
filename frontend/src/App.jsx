import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react'
import Dashboard from './Dashboard'
import SignalList from './SignalList'
import Stats from './Stats'

// Chart ใช้ lightweight-charts (~400KB) — lazy load เฉพาะตอนเปิดหน้า Chart
const Chart = lazy(() => import('./Chart'))

const API   = import.meta.env.VITE_API_URL  || 'http://localhost:8000'
const WSURL = import.meta.env.VITE_WS_URL   || 'ws://localhost:8000/ws'
const KEY   = import.meta.env.VITE_API_KEY  || ''

export const apiFetch = (path) =>
  fetch(`${API}${path}`, { headers: { 'X-API-Key': KEY } }).then(r => r.json())

const NAV_ITEMS = [
  { id: 'dashboard', label: '🏠 Home' },
  { id: 'chart',     label: '📈 Chart' },
  { id: 'signals',   label: '🔔 Signals' },
  { id: 'stats',     label: '📊 Stats' },
]

export default function App() {
  const [page, setPage]         = useState('dashboard')
  const [toasts, setToasts]     = useState([])
  const [newCount, setNewCount] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const wsRef = useRef(null)

  // ── WebSocket real-time ─────────────────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(WSURL)
    ws.onopen    = () => console.log('WS connected')
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'new_signal') {
          setNewCount(n => n + 1)
          addToast(`🥇 Signal ใหม่ #${data.signal_id}`)
        }
      } catch (_) {}
    }
    ws.onclose = () => setTimeout(connectWS, 3000)
    wsRef.current = ws
  }, [])

  useEffect(() => {
    connectWS()
    return () => wsRef.current?.close()
  }, [connectWS])

  // close hamburger on resize to desktop
  useEffect(() => {
    const handler = () => { if (window.innerWidth >= 768) setMenuOpen(false) }
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  // ── Toast ───────────────────────────────────────────────────
  const addToast = (msg) => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 5000)
  }

  const navigate = (target) => {
    setPage(target)
    if (target === 'signals') setNewCount(0)
    setMenuOpen(false)
  }

  return (
    <div className="layout">
      {/* ── Navbar ────────────────────────────────────────────── */}
      <nav className="navbar">
        <div className="navbar__brand" onClick={() => navigate('dashboard')}>
          🥇 <span>Gold Signal Tracker</span>
        </div>

        {/* Desktop nav */}
        <div className="nav-links nav-links--desktop">
          {NAV_ITEMS.map(item => (
            <a
              key={item.id}
              className={page === item.id ? 'active' : ''}
              onClick={() => navigate(item.id)}
            >
              {item.label}
              {item.id === 'signals' && newCount > 0 && (
                <span className="badge-new">{newCount}</span>
              )}
            </a>
          ))}
        </div>

        {/* Hamburger (mobile/tablet) */}
        <button
          className={`hamburger${menuOpen ? ' hamburger--open' : ''}`}
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
        >
          <span /><span /><span />
        </button>
      </nav>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div className="mobile-menu">
          {NAV_ITEMS.map(item => (
            <a
              key={item.id}
              className={`mobile-menu__item${page === item.id ? ' active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              {item.label}
              {item.id === 'signals' && newCount > 0 && (
                <span className="badge-new">{newCount}</span>
              )}
            </a>
          ))}
        </div>
      )}

      {/* ── Content ───────────────────────────────────────────── */}
      <main className="main">
        {page === 'dashboard' && <Dashboard apiFetch={apiFetch} onNavigate={navigate} />}
        {page === 'chart'     && (
          <Suspense fallback={<div className="loading">กำลังโหลด Chart...</div>}>
            <Chart apiFetch={apiFetch} />
          </Suspense>
        )}
        {page === 'signals'   && <SignalList apiFetch={apiFetch} />}
        {page === 'stats'     && <Stats     apiFetch={apiFetch} />}
      </main>

      {/* Toast notifications */}
      <div className="toast-wrap">
        {toasts.map(t => (
          <div key={t.id} className="toast">{t.msg}</div>
        ))}
      </div>
    </div>
  )
}
