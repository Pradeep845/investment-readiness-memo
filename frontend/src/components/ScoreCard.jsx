function scoreTone(score) {
  if (score >= 75) return { color: '#059669', label: 'Strong', soft: 'rgba(5, 150, 105, 0.12)' }
  if (score >= 55) return { color: '#d97706', label: 'Moderate', soft: 'rgba(217, 119, 6, 0.12)' }
  return { color: '#dc2626', label: 'Cautious', soft: 'rgba(220, 38, 38, 0.12)' }
}

function pillarTone(score) {
  if (score >= 70) return '#059669'
  if (score >= 50) return '#d97706'
  return '#dc2626'
}

function ScoreGauge({ score }) {
  const size = 168
  const stroke = 14
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, Number(score) || 0)) / 100
  const offset = c * (1 - pct)
  const tone = scoreTone(score)

  return (
    <div className="gauge-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="gauge">
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={tone.color} stopOpacity="0.95" />
            <stop offset="100%" stopColor={tone.color} stopOpacity="0.65" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#gaugeGrad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x="50%"
          y="46%"
          textAnchor="middle"
          dominantBaseline="central"
          className="gauge-num"
          fill="#0f172a"
        >
          {score}
        </text>
        <text
          x="50%"
          y="64%"
          textAnchor="middle"
          dominantBaseline="central"
          className="gauge-sub"
          fill="#64748b"
        >
          / 100
        </text>
      </svg>
    </div>
  )
}

function PillarBars({ pillars }) {
  if (!Array.isArray(pillars) || pillars.length === 0) return null
  return (
    <div className="hero-breakdown">
      <div className="hero-breakdown-head">
        <div className="card-eyebrow">Score breakdown</div>
        <h3 className="hero-breakdown-title">What drove the score</h3>
      </div>
      <ul className="pillar-list">
        {pillars.map((p) => {
          const score = Math.max(0, Math.min(100, Number(p.score) || 0))
          const color = pillarTone(score)
          return (
            <li key={p.key} className="pillar-row" title={p.note || ''}>
              <div className="pillar-head">
                <span className="pillar-label">{p.label}</span>
                <span className="pillar-value" style={{ color }}>{score}</span>
              </div>
              <div className="pillar-bar">
                <span className="pillar-bar-fill" style={{ width: `${score}%`, background: color }} />
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ScoreCard({ score, confidence, summary, pillars }) {
  const tone = scoreTone(score)

  return (
    <section className="card score-card full-width">
      <div className="score-grid">
        <div className="score-left">
          <ScoreGauge score={score} />
          <div className="score-pills">
            <span
              className="pill"
              style={{ background: tone.soft, color: tone.color, borderColor: tone.color }}
            >
              {tone.label} conviction
            </span>
            <span className="pill tone-mute">Confidence: {confidence}</span>
          </div>
        </div>
        <div className="score-meta">
          <div className="card-eyebrow">Executive summary</div>
          <h2 className="score-title">Readiness assessment</h2>
          <p className="score-summary">{summary}</p>
        </div>
        <PillarBars pillars={pillars} />
      </div>
    </section>
  )
}

export default ScoreCard
