const STATUS_LABEL = {
  ok: 'OK',
  empty: 'no signal',
  no_data: 'no data',
  not_requested: 'not requested',
  cancelled: 'cancelled',
  timeout: 'timed out',
  failed: 'failed',
  skipped: 'skipped',
  disabled: 'disabled',
}

const STATUS_TONE = {
  ok: 'tone-good',
  empty: 'tone-warn',
  no_data: 'tone-warn',
  not_requested: 'tone-mute',
  cancelled: 'tone-warn',
  timeout: 'tone-warn',
  failed: 'tone-bad',
  skipped: 'tone-mute',
  disabled: 'tone-mute',
}

const detail = (key, info) => {
  if (!info) return ''
  switch (key) {
    case 'map':
      if (info.urls_found != null) return `${info.urls_found} URLs discovered`
      if (info.fallback) return `Fallback: ${info.fallback}`
      return ''
    case 'scrape':
      if (info.pages_scraped != null) return `${info.pages_scraped} pages scraped`
      return ''
    case 'agentic':
      return ''
    case 'holocron':
      if (info.ok_slugs?.length) return info.ok_slugs.join(', ')
      if (info.total_rows) return `${info.total_rows} catalogs attempted`
      return ''
    case 'stock':
      if (info.ticker) return info.ticker
      return ''
    case 'gemini':
      if (info.key_facts != null) return `${info.key_facts} facts`
      return ''
    default:
      return ''
  }
}

const STAGE_ORDER = [
  ['map', 'Site Map'],
  ['scrape', 'Website Scrape'],
  ['agentic', 'Agentic Research'],
  ['holocron', 'Wire (Holocron)'],
  ['stock', 'Market Trend'],
  ['gemini', 'Synthesis'],
]

function Pipeline({ diagnostics }) {
  if (!diagnostics) return null
  const stages = diagnostics.stages || {}
  const timings = diagnostics.timings || {}

  const stageList = STAGE_ORDER.map(([key]) => stages[key] || { status: 'skipped' })
  const okCount = stageList.filter((s) => s.status === 'ok').length
  const totalCount = stageList.filter(
    (s) => s.status !== 'skipped' && s.status !== 'not_requested' && s.status !== 'disabled',
  ).length

  return (
    <section className="card full-width pipeline-card">
      <div className="pipeline-head">
        <div>
          <h2>Pipeline Run</h2>
          <p className="muted small">
            {okCount} of {totalCount} stages succeeded
          </p>
        </div>
        {timings.total_s != null && (
          <span className="pill tone-mute">Total {timings.total_s}s</span>
        )}
      </div>
      <div className="pipeline-bar" aria-hidden="true">
        {stageList.map((s, i) => {
          const tone = STATUS_TONE[s.status] || 'tone-mute'
          return <span key={i} className={`pipeline-segment ${tone}`} />
        })}
      </div>
      <ul className="pipeline-list">
        {STAGE_ORDER.map(([key, label]) => {
          const info = stages[key] || { status: 'skipped' }
          const tone = STATUS_TONE[info.status] || 'tone-mute'
          const statusLabel = STATUS_LABEL[info.status] || info.status
          const meta = detail(key, info)
          return (
            <li key={key} className="pipeline-stage">
              <span className={`status-dot ${tone}`} aria-hidden="true" />
              <div className="stage-body">
                <div className="stage-row">
                  <span className="stage-label">{label}</span>
                  <span className={`pill ${tone}`}>{statusLabel}</span>
                </div>
                {(meta || info.error) && (
                  <p className="muted small">{info.error ? `Error: ${info.error}` : meta}</p>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default Pipeline
