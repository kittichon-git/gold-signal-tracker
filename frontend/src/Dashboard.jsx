import { useState, useEffect } from 'react'

// ── Helpers ──────────────────────────────────────────────────────────────────
const CHANNEL_NAMES = {
  'Channel trades': 'EMpire',
  'trades': 'EMpire',
  '-1001680297592': 'EMpire',
}
const displayChannel = (name) => CHANNEL_NAMES[name] || name

const STATUS_LABEL = {
  tp1_hit: 'TP1 Hit', tp2_hit: 'TP2 Hit', sl_hit: 'SL Hit',
  open: 'Open', pending: 'Pending', missed: 'Missed', cancelled: 'Cancelled',
}
const STATUS_CLASS = {
  tp1_hit: 'badge-tp1', tp2_hit: 'badge-tp2', sl_hit: 'badge-sl',
  open: 'badge-open', pending: 'badge-pending', missed: 'badge-missed',
}

function StatCard({ icon, title, value, sub, color, onClick }) {
  return (
    <div className={`card stat-card${onClick ? ' stat-card--link' : ''}`} onClick={onClick}>
      <div className="stat-card__icon">{icon}</div>
      <div className="stat-card__body">
        <div className="card-title">{title}</div>
        <div className="card-value" style={{ color: color || 'var(--text)' }}>{value}</div>
        {sub && <div className="stat-card__sub">{sub}</div>}
      </div>
    </div>
  )
}

function PriceTicker({ price, change, pct }) {
  if (!price) return null
  const up = change >= 0
  return (
    <div className="price-ticker">
      <span className="price-ticker__label">XAU/USD</span>
      <span className="price-ticker__price">${price.toLocaleString('en', { minimumFractionDigits: 2 })}</span>
      <span className={`price-ticker__change ${up ? 'profit-pos' : 'profit-neg'}`}>
        {up ? '▲' : '▼'} {Math.abs(change).toFixed(2)} ({up ? '+' : ''}{pct.toFixed(2)}%)
      </span>
      <span className="price-ticker__dot" style={{ background: 'var(--green)' }} />
      <span style={{ fontSize: 11, color: 'var(--muted)' }}>Live</span>
    </div>
  )
}

function RecentSignalRow({ s, isMobile }) {
  const t = new Date(s.signal_time)
  const timeStr = isMobile
    ? t.toLocaleDateString('th-TH', { month: 'short', day: 'numeric' })
    : t.toLocaleString('th-TH', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  return (
    <tr>
      <td><span className={s.action === 'buy' ? 'buy' : 'sell'}>{s.action?.toUpperCase()}</span></td>
      <td>{s.entry_price?.toLocaleString('en', { minimumFractionDigits: 2 })}</td>
      {!isMobile && <td style={{ color: 'var(--muted)', fontSize: 12 }}>{displayChannel(s.channel_name) || '—'}</td>}
      <td>
        <span className={`badge ${STATUS_CLASS[s.order_status] || 'badge-pending'}`}>
          {STATUS_LABEL[s.order_status] || s.order_status}
        </span>
      </td>
      <td style={{ color: 'var(--muted)', fontSize: 12, whiteSpace: 'nowrap' }}>{timeStr}</td>
    </tr>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ apiFetch, onNavigate }) {
  const [summary, setSummary]     = useState(null)
  const [signals, setSignals]     = useState([])
  const [channels, setChannels]   = useState([])
  const [price, setPrice]         = useState(null)
  const [loading, setLoading]     = useState(true)
  const [isMobile, setIsMobile]   = useState(window.innerWidth < 600)
  const [isTablet, setIsTablet]   = useState(window.innerWidth < 1024)

  // responsive resize listener
  useEffect(() => {
    const handler = () => {
      setIsMobile(window.innerWidth < 600)
      setIsTablet(window.innerWidth < 1024)
    }
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      apiFetch('/api/stats/daily?days=7'),
      apiFetch('/api/signals?limit=8&page=1'),
      apiFetch('/api/channels/compare'),
      apiFetch('/api/price/latest'),
    ]).then(([dailyR, signalsR, compareR, priceR]) => {
      // daily → compute 7-day summary
      const daily = dailyR.status === 'fulfilled' ? (dailyR.value || []) : []
      const total  = daily.reduce((s, d) => s + (d.total  || 0), 0)
      const wins   = daily.reduce((s, d) => s + (d.wins   || 0), 0)
      const losses = daily.reduce((s, d) => s + (d.losses || 0), 0)
      const profit = daily.reduce((s, d) => s + (d.total_profit || 0), 0)
      setSummary({ total, wins, losses, profit, winRate: total > 0 ? (wins / total * 100).toFixed(1) : '0.0' })

      // signals
      const sigData = signalsR.status === 'fulfilled' ? signalsR.value : {}
      setSignals(sigData.data || [])

      // channels
      const cmp = compareR.status === 'fulfilled' ? (compareR.value || []) : []
      setChannels(cmp.slice(0, isMobile ? 3 : 5))

      // price
      const p = priceR.status === 'fulfilled' ? priceR.value : null
      if (p?.close) setPrice(p)

      setLoading(false)
    })
  }, [])

  // count active signals
  const activeCount = signals.filter(s => ['open', 'pending'].includes(s.order_status)).length

  return (
    <div className="dashboard">
      {/* ── Hero bar ──────────────────────────────────────────────── */}
      <div className="dashboard__hero">
        <div className="dashboard__hero-left">
          <h2 className="dashboard__title">Dashboard</h2>
          <p className="dashboard__subtitle">ภาพรวม 7 วันล่าสุด</p>
        </div>
        {price && (
          <PriceTicker
            price={price.close}
            change={(price.close - price.open)}
            pct={((price.close - price.open) / price.open * 100)}
          />
        )}
      </div>

      {loading ? (
        <div className="loading">กำลังโหลด...</div>
      ) : (
        <>
          {/* ── Summary cards ─────────────────────────────────────── */}
          <div className="dashboard__stats">
            <StatCard
              icon="📊"
              title="Signals (7 วัน)"
              value={summary?.total?.toLocaleString() || '0'}
              sub={`W ${summary?.wins} / L ${summary?.losses}`}
              onClick={() => onNavigate('signals')}
            />
            <StatCard
              icon="🎯"
              title="Win Rate"
              value={`${summary?.winRate}%`}
              color={parseFloat(summary?.winRate) >= 50 ? 'var(--green)' : 'var(--red)'}
              sub="7 วันล่าสุด"
            />
            <StatCard
              icon="⚡"
              title="Active"
              value={activeCount}
              sub="Pending / Open"
              color={activeCount > 0 ? 'var(--blue)' : 'var(--muted)'}
              onClick={() => onNavigate('signals')}
            />
            <StatCard
              icon="💰"
              title="Total Profit"
              value={`${(summary?.profit || 0) >= 0 ? '+' : ''}${(summary?.profit || 0).toFixed(1)} pts`}
              color={(summary?.profit || 0) >= 0 ? 'var(--green)' : 'var(--red)'}
              sub="7 วันล่าสุด"
            />
          </div>

          {/* ── Two-column section ────────────────────────────────── */}
          <div className={`dashboard__grid ${isTablet ? 'dashboard__grid--single' : ''}`}>

            {/* Recent Signals */}
            <div className="card">
              <div className="dashboard__section-header">
                <span className="card-title" style={{ marginBottom: 0 }}>Signals ล่าสุด</span>
                <button className="link-btn" onClick={() => onNavigate('signals')}>ดูทั้งหมด →</button>
              </div>
              {signals.length === 0 ? (
                <div className="empty-state">ยังไม่มีสัญญาณ</div>
              ) : (
                <div className="table-wrap" style={{ marginTop: 12 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Action</th>
                        <th>Entry</th>
                        {!isMobile && <th>Channel</th>}
                        <th>Status</th>
                        <th>เวลา</th>
                      </tr>
                    </thead>
                    <tbody>
                      {signals.slice(0, isMobile ? 5 : 8).map(s => (
                        <RecentSignalRow key={s.id} s={s} isMobile={isMobile} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Channel Ranking */}
            <div className="card">
              <div className="dashboard__section-header">
                <span className="card-title" style={{ marginBottom: 0 }}>Channel Ranking</span>
                <button className="link-btn" onClick={() => onNavigate('stats')}>ดูสถิติ →</button>
              </div>
              {channels.length === 0 ? (
                <div className="empty-state">ยังไม่มีข้อมูล</div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  {channels.map((c, i) => (
                    <div key={c.channel_name} className="channel-row">
                      <div className="channel-row__rank">#{i + 1}</div>
                      <div className="channel-row__info">
                        <div className="channel-row__name">{displayChannel(c.channel_name)}</div>
                        <div className="channel-row__meta">
                          <span>{c.total} signals</span>
                          <span className={c.win_rate >= 50 ? 'profit-pos' : 'profit-neg'}>
                            WR {c.win_rate}%
                          </span>
                          <span className={(c.total_profit || 0) >= 0 ? 'profit-pos' : 'profit-neg'}>
                            {(c.total_profit || 0) >= 0 ? '+' : ''}{(c.total_profit || 0).toFixed(1)} pts
                          </span>
                        </div>
                        <div className="channel-row__bar">
                          <div
                            className="channel-row__bar-fill"
                            style={{
                              width: `${Math.min(Math.abs(c.total_profit || 0) / Math.max(...channels.map(x => Math.abs(x.total_profit || 0)), 1) * 100, 100)}%`,
                              background: (c.total_profit || 0) >= 0 ? 'var(--green)' : 'var(--red)',
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Quick nav (mobile/tablet only) ───────────────────── */}
          {isTablet && (
            <div className="quick-nav">
              <button className="quick-nav__btn" onClick={() => onNavigate('chart')}>
                <span>📈</span><span>Chart</span>
              </button>
              <button className="quick-nav__btn" onClick={() => onNavigate('signals')}>
                <span>🔔</span><span>Signals</span>
              </button>
              <button className="quick-nav__btn" onClick={() => onNavigate('stats')}>
                <span>📊</span><span>Stats</span>
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
