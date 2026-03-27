import { useState, useEffect, useCallback } from 'react'

const BADGE = {
  tp1_hit: ['badge badge-tp1', 'TP1 Hit'],
  tp2_hit: ['badge badge-tp2', 'TP2 Hit'],
  sl_hit:  ['badge badge-sl',  'SL Hit'],
  open:    ['badge badge-open','Open'],
  pending: ['badge badge-pending','Pending'],
  missed:  ['badge badge-missed', 'Missed'],
  cancelled: ['badge badge-missed','Cancelled'],
}

export default function SignalList({ apiFetch }) {
  const [data,     setData]     = useState({ total: 0, data: [] })
  const [page,     setPage]     = useState(1)
  const [loading,  setLoading]  = useState(true)
  const [channels, setChannels] = useState([])

  const [filters, setFilters] = useState({
    channel: '', status: '', action: '',
    from_date: '', to_date: '',
  })

  const setFilter = (k, v) => {
    setFilters(f => ({ ...f, [k]: v }))
    setPage(1)
  }

  const load = useCallback(() => {
    setLoading(true)
    const p = new URLSearchParams({ page, limit: 50 })
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v))
    apiFetch(`/api/signals?${p}`).then(d => {
      setData(d || { total: 0, data: [] })
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [page, filters])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    apiFetch('/api/channels').then(d => setChannels(d || []))
  }, [])

  const totalPages = Math.ceil(data.total / 50)

  return (
    <div>
      {/* Summary row */}
      <div style={{ color: 'var(--muted)', marginBottom: 12, fontSize: 13 }}>
        ทั้งหมด <b style={{ color: 'var(--text)' }}>{data.total.toLocaleString()}</b> signals
      </div>

      {/* Filters */}
      <div className="filters">
        <select value={filters.channel} onChange={e => setFilter('channel', e.target.value)}>
          <option value="">All Channels</option>
          {channels.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>
        <select value={filters.action} onChange={e => setFilter('action', e.target.value)}>
          <option value="">Buy & Sell</option>
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>
        <select value={filters.status} onChange={e => setFilter('status', e.target.value)}>
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="open">Open</option>
          <option value="tp1_hit">TP1 Hit</option>
          <option value="tp2_hit">TP2 Hit</option>
          <option value="sl_hit">SL Hit</option>
          <option value="missed">Missed</option>
        </select>
        <input type="date" placeholder="From"
          value={filters.from_date} onChange={e => setFilter('from_date', e.target.value)} />
        <input type="date" placeholder="To"
          value={filters.to_date} onChange={e => setFilter('to_date', e.target.value)} />
      </div>

      {loading ? (
        <div className="loading">กำลังโหลด...</div>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>เวลา</th>
                  <th>Channel</th>
                  <th>Buy/Sell</th>
                  <th>Entry</th>
                  <th>TP1</th>
                  <th>TP2</th>
                  <th>SL</th>
                  <th>R/R</th>
                  <th>สถานะ</th>
                  <th>กำไร/ขาดทุน</th>
                  <th>Conf.</th>
                </tr>
              </thead>
              <tbody>
                {data.data.length === 0 ? (
                  <tr><td colSpan={12} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>
                    ไม่พบข้อมูล
                  </td></tr>
                ) : data.data.map(s => {
                  const [cls, label] = BADGE[s.order_status] || ['badge', s.order_status]
                  const profit = s.profit_points
                  return (
                    <tr key={s.id} title={s.raw_message || ''}>
                      <td style={{ color: 'var(--muted)' }}>{s.id}</td>
                      <td style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                        {s.signal_time?.slice(0, 16)}
                      </td>
                      <td>{s.channel_name}</td>
                      <td className={s.action}>{s.action?.toUpperCase()}</td>
                      <td><b>{s.entry_price}</b></td>
                      <td style={{ color: 'var(--green)' }}>{s.tp1 ?? '—'}</td>
                      <td style={{ color: 'var(--green)' }}>{s.tp2 ?? '—'}</td>
                      <td style={{ color: 'var(--red)'   }}>{s.sl  ?? '—'}</td>
                      <td style={{ color: 'var(--muted)' }}>{s.risk_reward_ratio ?? '—'}</td>
                      <td><span className={cls}>{label}</span></td>
                      <td className={profit == null ? '' : profit >= 0 ? 'profit-pos' : 'profit-neg'}>
                        {profit == null ? '—' : `${profit >= 0 ? '+' : ''}${profit}`}
                      </td>
                      <td style={{ color: 'var(--muted)' }}>
                        {s.confidence_score != null
                          ? `${(s.confidence_score * 100).toFixed(0)}%` : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <span style={{ color: 'var(--muted)' }}>
              หน้า {page} / {totalPages || 1}
            </span>
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← ก่อนหน้า</button>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>ถัดไป →</button>
          </div>
        </>
      )}
    </div>
  )
}
