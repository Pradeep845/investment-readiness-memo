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

  const preview = data.points.slice(-8)
  const directionLabel = data.direction.toUpperCase()

  return (
    <section className="card">
      <div className="stock-head">
        <h2>Market Trend · {data.ticker}</h2>
        <span className={`pill ${data.direction}`}>{directionLabel}</span>
      </div>
      <p className="muted">30-day change: {data.change_percent}%</p>
      <div className="sparkline">
        {preview.map((point) => (
          <span key={point.timestamp} title={`${point.timestamp}: ${point.close}`}>
            {point.close}
          </span>
        ))}
      </div>
    </section>
  )
}

export default StockTrend
