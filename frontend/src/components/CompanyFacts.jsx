const ORDER = [
  { key: 'revenue', label: 'Revenue' },
  { key: 'market_cap', label: 'Market cap' },
  { key: 'employees', label: 'Employees' },
  { key: 'industry', label: 'Industry' },
  { key: 'founded', label: 'Founded' },
  { key: 'headquarters', label: 'Headquarters' },
  { key: 'ceo', label: 'CEO' },
]

function CompanyFacts({ snapshot }) {
  const data = snapshot || {}
  const rows = ORDER.filter((row) => {
    const v = data[row.key]
    return typeof v === 'string' && v.trim().length > 0
  })

  if (rows.length === 0) return null

  return (
    <section className="card facts-card">
      <div className="card-eyebrow">Company snapshot</div>
      <h2>Key company facts</h2>
      <div className="facts-grid">
        {rows.map((row) => (
          <div key={row.key} className="fact-tile">
            <div className="fact-label muted small">{row.label}</div>
            <div className="fact-value">{data[row.key]}</div>
          </div>
        ))}
      </div>
      <div className="muted small fact-source">
        Pulled directly from Wikipedia / news / website evidence above.
      </div>
    </section>
  )
}

export default CompanyFacts
