import { useEffect, useRef, useState } from 'react'
import { createChart, CrosshairMode } from 'lightweight-charts'

const STATUS_COLOR = {
  tp1_hit: '#3fb950', tp2_hit: '#4dbb5f',
  sl_hit:  '#f85149', open:    '#58a6ff',
  missed:  '#8b949e', pending: '#d29922',
}

export default function Chart({ apiFetch }) {
  const containerRef = useRef(null)
  const chartRef     = useRef(null)
  const candleRef    = useRef(null)
  const priceLines   = useRef([])

  const [channel,   setChannel]   = useState('')
  const [action,    setAction]    = useState('')
  const [fromDate,  setFromDate]  = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 7)
    return d.toISOString().slice(0, 10)
  })
  const [toDate,    setToDate]    = useState(() => new Date().toISOString().slice(0, 10))
  const [channels,  setChannels]  = useState([])
  const [loading,   setLoading]   = useState(true)
  const [hoverInfo, setHoverInfo] = useState(null)

  // ── Init chart ───────────────────────────────────────────────
  useEffect(() => {
    const chart = createChart(containerRef.current, {
      layout:      { background: { color: '#0d1117' }, textColor: '#e6edf3' },
      grid:        { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      crosshair:   { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#30363d' },
      timeScale:   { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
      width:       containerRef.current.clientWidth,
      height:      480,
    })

    const series = chart.addCandlestickSeries({
      upColor:        '#3fb950', downColor: '#f85149',
      borderUpColor:  '#3fb950', borderDownColor: '#f85149',
      wickUpColor:    '#3fb950', wickDownColor: '#f85149',
    })

    chartRef.current  = chart
    candleRef.current = series

    // Crosshair info
    chart.subscribeCrosshairMove(param => {
      if (param.point && param.seriesData?.size > 0) {
        const d = param.seriesData.get(series)
        if (d) setHoverInfo(d)
      }
    })

    // Resize observer
    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { chart.remove(); ro.disconnect() }
  }, [])

  // ── Load channels ────────────────────────────────────────────
  useEffect(() => {
    apiFetch('/api/channels').then(data => setChannels(data || []))
  }, [])

  // ── Load data ────────────────────────────────────────────────
  useEffect(() => {
    if (!chartRef.current) return
    setLoading(true)

    const from = `${fromDate} 00:00:00`
    const to   = `${toDate} 23:59:59`

    Promise.all([
      apiFetch(`/api/prices?from_date=${encodeURIComponent(from)}&to_date=${encodeURIComponent(to)}&interval=1h`),
      apiFetch(`/api/signals/markers?from_date=${encodeURIComponent(from)}&to_date=${encodeURIComponent(to)}`)
    ]).then(([prices, signals]) => {
      // ── Candles ──────────────────────────────────────────────
      const candles = (prices || []).map(p => ({
        time:  Math.floor(new Date(p.time).getTime() / 1000),
        open:  p.open, high: p.high, low: p.low, close: p.close,
      })).filter(c => c.time)
      candleRef.current.setData(candles)

      // ── Clear old price lines ─────────────────────────────────
      priceLines.current.forEach(pl => {
        try { candleRef.current.removePriceLine(pl) } catch (_) {}
      })
      priceLines.current = []

      // ── Signal markers + price lines ─────────────────────────
      const filtered = (signals || []).filter(s =>
        (!channel || s.channel_name === channel) &&
        (!action  || s.action === action)
      )

      const markers = filtered.map(s => ({
        time:     Math.floor(new Date(s.signal_time).getTime() / 1000),
        position: s.action === 'buy' ? 'belowBar' : 'aboveBar',
        color:    STATUS_COLOR[s.order_status] || '#d29922',
        shape:    s.action === 'buy' ? 'arrowUp' : 'arrowDown',
        text:     `${s.action.toUpperCase()} ${s.entry_price}`,
        size:     1.5,
      }))
      candleRef.current.setMarkers(markers)

      // วาดเส้น TP/SL สำหรับ signal ที่ยังเปิดอยู่
      filtered.filter(s => s.order_status === 'open').forEach(s => {
        if (s.tp1) priceLines.current.push(
          candleRef.current.createPriceLine({ price: s.tp1, color: '#3fb950',
            lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'TP1' }))
        if (s.tp2) priceLines.current.push(
          candleRef.current.createPriceLine({ price: s.tp2, color: '#4dbb5f',
            lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'TP2' }))
        if (s.sl)  priceLines.current.push(
          candleRef.current.createPriceLine({ price: s.sl,  color: '#f85149',
            lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'SL'  }))
      })

      chartRef.current.timeScale().fitContent()
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [fromDate, toDate, channel, action])

  return (
    <div>
      {/* Filters */}
      <div className="filters">
        <select value={channel} onChange={e => setChannel(e.target.value)}>
          <option value="">All Channels</option>
          {channels.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>
        <select value={action} onChange={e => setAction(e.target.value)}>
          <option value="">Buy & Sell</option>
          <option value="buy">Buy Only</option>
          <option value="sell">Sell Only</option>
        </select>
        <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} />
        <span style={{ color: 'var(--muted)', alignSelf: 'center' }}>→</span>
        <input type="date" value={toDate}   onChange={e => setToDate(e.target.value)} />
      </div>

      {/* OHLC hover info */}
      {hoverInfo && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 8, fontSize: 13, color: 'var(--muted)' }}>
          <span>O <b style={{ color: 'var(--text)' }}>{hoverInfo.open}</b></span>
          <span>H <b style={{ color: 'var(--green)' }}>{hoverInfo.high}</b></span>
          <span>L <b style={{ color: 'var(--red)' }}>{hoverInfo.low}</b></span>
          <span>C <b style={{ color: 'var(--text)' }}>{hoverInfo.close}</b></span>
        </div>
      )}

      {/* Chart */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        background: 'rgba(13,17,23,.7)', zIndex: 10,
                        color: 'var(--muted)' }}>
            Loading...
          </div>
        )}
        <div ref={containerRef} />
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 12, color: 'var(--muted)' }}>
        {Object.entries(STATUS_COLOR).map(([k, v]) => (
          <span key={k}><span style={{ color: v }}>●</span> {k.replace('_', ' ')}</span>
        ))}
      </div>
    </div>
  )
}
