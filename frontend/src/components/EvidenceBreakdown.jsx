const SOURCE_GROUPS = [
  { key: 'website', label: 'Website', color: '#2563eb', test: (s) => s === 'url-scraper' },
  { key: 'wikipedia', label: 'Wikipedia', color: '#7c3aed', test: (s) => s.includes('wp_') },
  { key: 'news', label: 'News', color: '#0891b2', test: (s) => s.includes('gn_') },
  { key: 'other', label: 'Other Wire', color: '#475569', test: (s) => s.startsWith('holocron:') },
]

function classify(source) {
  const s = (source || '').toLowerCase()
  for (const g of SOURCE_GROUPS) {
    if (g.test(s)) return g.key
  }
  return 'other'
}

function Donut({ slices, size = 168, thickness = 22 }) {
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  const total = slices.reduce((s, x) => s + x.value, 0) || 1
  let acc = 0

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut">
      <g transform={`translate(${size / 2}, ${size / 2}) rotate(-90)`}>
        <circle r={r} fill="none" stroke="#e2e8f0" strokeWidth={thickness} />
        {slices.map((slice) => {
          if (slice.value <= 0) return null
          const seg = (slice.value / total) * c
          const dash = `${seg} ${c - seg}`
          const offset = -acc
          acc += seg
          return (
            <circle
              key={slice.key}
              r={r}
              fill="none"
              stroke={slice.color}
              strokeWidth={thickness}
              strokeDasharray={dash}
              strokeDashoffset={offset}
              strokeLinecap="butt"
            />
          )
        })}
      </g>
      <text x="50%" y="46%" textAnchor="middle" dominantBaseline="central" className="donut-num" fill="#0f172a">
        {total}
      </text>
      <text x="50%" y="62%" textAnchor="middle" dominantBaseline="central" className="donut-sub" fill="#64748b">
        sources
      </text>
    </svg>
  )
}

function EvidenceBreakdown({ items }) {
  if (!items || items.length === 0) return null
  const counts = { website: 0, wikipedia: 0, news: 0, other: 0 }
  for (const it of items) counts[classify(it.source)] += 1

  const slices = SOURCE_GROUPS.map((g) => ({
    key: g.key,
    label: g.label,
    color: g.color,
    value: counts[g.key],
  })).filter((s) => s.value > 0)

  if (slices.length === 0) return null
  const total = items.length

  return (
    <section className="card breakdown-card">
      <div className="card-eyebrow">Evidence mix</div>
      <h2>How the memo is sourced</h2>
      <div className="breakdown-body">
        <Donut slices={slices} size={140} thickness={20} />
        <ul className="legend">
          {slices.map((s) => (
            <li key={s.key}>
              <span className="legend-dot" style={{ background: s.color }} aria-hidden="true" />
              <span className="legend-label">{s.label}</span>
              <span className="legend-value">
                {s.value}
                <span className="muted small"> · {Math.round((s.value / total) * 100)}%</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export default EvidenceBreakdown
