function StockTrend({ data }) {
  if (!data) {
    return (
      <section className="card">
        <h2>Stock Trend</h2>
        <p className="muted">No ticker provided or stock trend unavailable.</p>
      </section>
    )
  }

  const preview = data.points.slice(-8)

  return (
    <section className="card">
      <h2>Stock Trend ({data.ticker})</h2>
      <p className={`pill ${data.direction}`}>{data.direction.toUpperCase()}</p>
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
