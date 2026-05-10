function LineChart({ points, direction }) {
  if (!points || points.length < 2) return null

  const width = 320
  const height = 90
  const padX = 6
  const padY = 8

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

function StockTrend({ data, ticker }) {
  if (!data) {
    const enteredTicker = (ticker || '').trim().toUpperCase()
    return (
      <section className="card">
        <h2>Market Trend</h2>
        {enteredTicker ? (
          <p className="muted">
            Could not fetch a 30-day trend for <strong>{enteredTicker}</strong>. Double-check the symbol
            (Yahoo / Stooq format, e.g. <code>NVDA</code>, <code>AAPL</code>, <code>TSLA</code>).
          </p>
        ) : (
          <p className="muted">
            Enter a stock ticker (e.g. <code>NVDA</code>, <code>AAPL</code>) above to layer a 30-day price
            trend onto the memo.
          </p>
        )}
      </section>
    )
  }

  const last = data.points[data.points.length - 1]
  const first = data.points[0]
  const directionLabel = data.direction.toUpperCase()

  return (
    <section className="card">
      <div className="stock-head">
        <h2>Market Trend · {data.ticker}</h2>
        <span className={`pill ${data.direction}`}>{directionLabel}</span>
      </div>
      <div className="stock-numbers">
        <div>
          <div className="muted small">30-day change</div>
          <div className={`stock-change tone-${data.direction === 'up' ? 'good' : data.direction === 'down' ? 'bad' : 'warn'}`}>
            {data.change_percent > 0 ? '+' : ''}
            {data.change_percent}%
          </div>
        </div>
        <div className="stock-range">
          <div className="muted small">{first?.timestamp} — {last?.timestamp}</div>
          <div className="muted small">
            {first?.close} → <strong>{last?.close}</strong>
          </div>
        </div>
      </div>
      <LineChart points={data.points} direction={data.direction} />
    </section>
  )
}

export default StockTrend
