import { useState, useEffect } from 'react'

function StatCard({ title, value, sub, color }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="card-value" style={{ color: color || 'var(--text)' }}>{value}</div>
      {sub && <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function MiniBar({ value, max, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div style={{ background: 'var(--bg)', borderRadius: 4, height: 8, width: '100%', overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4, transition: 'width .3s' }} />
    </div>
  )
}

export default function Stats({ apiFetch }) {
  const [daily,   setDaily]   = useState([])
  const [compare, setCompare] = useState([])
  const [loading, setLoading] = useState(true)
  const [days,    setDays]    = useState(30)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      apiFetch(`/api/stats/daily?days=${days}`),
      apiFetch('/api/channels/compare'),
    ]).then(([d, c]) => {
      setDaily(d   || [])
      setCompare(c || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [days])

  // ── Summary calculation ──────────────────────────────────────
  const total  = daily.reduce((s, d) => s + (d.total  || 0), 0)
  const wins   = daily.reduce((s, d) => s + (d.wins   || 0), 0)
  const losses = daily.reduce((s, d) => s + (d.losses || 0), 0)
  const profit = daily.reduce((s, d) => s + (d.total_profit || 0), 0)
  const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) : '0.0'
  const maxProfit = Math.max(...daily.map(d => Math.abs(d.total_profit || 0)), 1)
  const maxCompareProfit = Math.max(...compare.map(c => Math.abs(c.total_profit || 0)), 1)

  return (
    <div>
      {/* Period selector */}
      <div className="filters" style={{ marginBottom: 16 }}>
        {[7, 30, 90, 365].map(d => (
          <button key={d}
            onClick={() => setDays(d)}
            style={{
              background: days === d ? 'var(--blue)' : 'var(--surface)',
              border: `1px solid ${days === d ? 'var(--blue)' : 'var(--border)'}`,
              color: 'var(--text)', padding: '5px 14px', borderRadius: 'var(--radius)',
              cursor: 'pointer',
            }}>
            {d === 365 ? '1 ปี' : `${d} วัน`}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">กำลังโหลด...</div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <StatCard title="Signals ทั้งหมด"  value={total.toLocaleString()} />
            <StatCard title="Win Rate"   value={`${winRate}%`}
              color={parseFloat(winRate) >= 50 ? 'var(--green)' : 'var(--red)'} />
            <StatCard title="Total Profit"
              value={`${profit >= 0 ? '+' : ''}${profit.toFixed(1)} pts`}
              color={profit >= 0 ? 'var(--green)' : 'var(--red)'} />
            <StatCard title="W / L"
              value={`${wins} / ${losses}`}
              sub={`Missed: ${total - wins - losses}`} />
          </div>

          <div className="grid-2">
            {/* Daily breakdown */}
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>รายวัน ({days} วันล่าสุด)</div>
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                <table style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>วันที่</th>
                      <th>Signals</th>
                      <th>Win Rate</th>
                      <th>Profit</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {daily.length === 0 ? (
                      <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--muted)', padding: 20 }}>
                        ไม่มีข้อมูล
                      </td></tr>
                    ) : daily.map(d => {
                      const wr = d.total > 0 ? ((d.wins / d.total) * 100).toFixed(0) : 0
                      const p  = d.total_profit || 0
                      return (
                        <tr key={d.date}>
                          <td style={{ whiteSpace: 'nowrap' }}>{d.date}</td>
                          <td>{d.total}</td>
                          <td style={{ color: wr >= 50 ? 'var(--green)' : 'var(--red)' }}>
                            {wr}%
                          </td>
                          <td className={p >= 0 ? 'profit-pos' : 'profit-neg'}>
                            {p >= 0 ? '+' : ''}{p.toFixed(1)}
                          </td>
                          <td style={{ width: 80 }}>
                            <MiniBar value={Math.abs(p)} max={maxProfit}
                              color={p >= 0 ? 'var(--green)' : 'var(--red)'} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Channel ranking */}
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Channel Ranking</div>
              {compare.length === 0 ? (
                <div style={{ color: 'var(--muted)', padding: 20, textAlign: 'center' }}>
                  ไม่มีข้อมูล
                </div>
              ) : compare.map((c, i) => (
                <div key={c.channel_name} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span>
                      <span style={{ color: 'var(--gold)', marginRight: 8 }}>#{i + 1}</span>
                      {c.channel_name}
                    </span>
                    <span style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {c.total} signals | WR: <b style={{ color: c.win_rate >= 50 ? 'var(--green)' : 'var(--red)' }}>
                        {c.win_rate}%
                      </b>
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <MiniBar value={Math.abs(c.total_profit || 0)} max={maxCompareProfit}
                      color={(c.total_profit || 0) >= 0 ? 'var(--green)' : 'var(--red)'} />
                    <span className={(c.total_profit || 0) >= 0 ? 'profit-pos' : 'profit-neg'}
                      style={{ whiteSpace: 'nowrap', fontSize: 13 }}>
                      {(c.total_profit || 0) >= 0 ? '+' : ''}{(c.total_profit || 0).toFixed(1)} pts
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
