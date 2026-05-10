function LineChart({ points, direction }) {
  if (!points || points.length < 2) return null

  const width = 320
  const height = 96
  const padX = 6
  const padY = 10

  const closes = points.map((p) => p.close)
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const range = max - min || 1
  const stepX = (width - padX * 2) / (points.length - 1)

  const xy = points.map((p, i) => {
    const x = padX + i * stepX
    const y = padY + (height - padY * 2) * (1 - (p.close - min) / range)
    return [x, y]
  })

  const linePath = xy.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`).join(' ')
  const areaPath = `${linePath} L ${xy[xy.length - 1][0].toFixed(2)} ${height - padY} L ${xy[0][0].toFixed(2)} ${height - padY} Z`

  const stroke = direction === 'up' ? '#059669' : direction === 'down' ? '#dc2626' : '#d97706'
  const fillId = `stockFill-${direction}`

  return (
    <svg width="100%" height={height + 4} viewBox={`0 0 ${width} ${height + 4}`} preserveAspectRatio="none" className="line-chart">
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${fillId})`} stroke="none" />
      <path d={linePath} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {xy.map(([x, y], i) =>
        i === 0 || i === xy.length - 1 ? (
          <circle key={i} cx={x} cy={y} r="3" fill="#fff" stroke={stroke} strokeWidth="2" />
        ) : null,
      )}
    </svg>
  )
}

function fmtPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value}%`
}

function fmtPrice(value, currency) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : ''
  return `${symbol}${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function tone(direction) {
  return direction === 'up' ? 'good' : direction === 'down' ? 'bad' : 'warn'
}

function StockTrend({ data, diagnostics }) {
  if (!data) {
    const stage = diagnostics?.stages?.stock || {}
    const attemptedTicker = stage.ticker || diagnostics?.stock_ticker
    return (
      <section className="card stock-card">
        <div className="card-eyebrow">Market</div>
        <h2>Market trend</h2>
        {attemptedTicker ? (
          <p className="muted">
            We located a public listing (<strong>{attemptedTicker}</strong>) but the live data feed did
            not respond in time. Re-running the memo usually recovers the trend.
          </p>
        ) : (
          <p className="muted">
            No publicly traded listing was confidently matched for this company. This is expected for
            private firms, early-stage startups, or subsidiaries — the memo continues to rely on
            evidence from the website, agentic research, and Wire signals.
          </p>
        )}
      </section>
    )
  }

  const last = data.points[data.points.length - 1]
  const first = data.points[0]
  const directionLabel = data.direction.toUpperCase()
  const todayDir = (data.today_change_percent ?? 0) > 1 ? 'up' : (data.today_change_percent ?? 0) < -1 ? 'down' : 'flat'

  return (
    <section className="card stock-card">
      <div className="stock-head">
        <div>
          <div className="card-eyebrow">Market</div>
          <h2>
            {data.ticker}
            {data.exchange ? <span className="muted small"> · {data.exchange}</span> : null}
          </h2>
          {data.auto_resolved ? (
            <span className="pill tone-mute auto-pill" title="Ticker matched automatically from the company name via Yahoo Finance.">
              auto-detected
            </span>
          ) : null}
        </div>
        <span className={`pill ${data.direction}`}>30D {directionLabel}</span>
      </div>

      <div className="stock-price">
        <div className="stock-price-main">{fmtPrice(data.current_price ?? last?.close, data.currency)}</div>
        <div className={`stock-price-sub tone-${tone(todayDir)}`}>
          {fmtPct(data.today_change_percent)} <span className="muted small">today</span>
        </div>
      </div>

      <div className="stock-stats">
        <div className="stock-stat">
          <div className="muted small">30-day</div>
          <div className={`stock-stat-val tone-${tone(data.direction)}`}>{fmtPct(data.change_percent)}</div>
        </div>
        <div className="stock-stat">
          <div className="muted small">Prev close</div>
          <div className="stock-stat-val">{fmtPrice(data.previous_close, data.currency)}</div>
        </div>
        <div className="stock-stat">
          <div className="muted small">30D low → high</div>
          <div className="stock-stat-val">
            {fmtPrice(Math.min(...data.points.map((p) => p.close)), data.currency)} →{' '}
            {fmtPrice(Math.max(...data.points.map((p) => p.close)), data.currency)}
          </div>
        </div>
      </div>

      <LineChart points={data.points} direction={data.direction} />
      <div className="stock-range muted small">
        {first?.timestamp} — {last?.timestamp}
      </div>
    </section>
  )
}

export default StockTrend
