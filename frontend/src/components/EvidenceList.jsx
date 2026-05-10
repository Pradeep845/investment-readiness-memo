const SOURCE_LABELS = {
  'url-scraper': 'Website',
  'holocron:wp_search': 'Wikipedia',
  'holocron:gn_related': 'Google News',
  'holocron:gn_article': 'Google News',
  'holocron:gn_source': 'Publisher',
  'holocron:gn_local': 'Local News',
}

const looksLikeJson = (value) => {
  if (typeof value !== 'string') return false
  const trimmed = value.trim()
  return trimmed.startsWith('{') || trimmed.startsWith('[')
}

const cleanSnippet = (snippet) => {
  if (!snippet) return 'No snippet available.'
  if (looksLikeJson(snippet)) {
    return 'Structured data captured (open the diagnostics panel for the raw payload).'
  }
  return snippet
}

const sourceLabel = (raw) => {
  if (!raw) return 'Source'
  if (SOURCE_LABELS[raw]) return SOURCE_LABELS[raw]
  if (raw.startsWith('holocron:')) return `Wire · ${raw.slice('holocron:'.length)}`
  return raw
}

function EvidenceList({ items }) {
  return (
    <section className="card full-width">
      <h2>Evidence</h2>
      {items?.length ? (
        <ul className="evidence-list">
          {items.map((item, index) => (
            <li key={`${item.url}-${index}`}>
              <div className="evidence-head">
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
                <span className="pill source-pill">{sourceLabel(item.source)}</span>
              </div>
              <p className="muted">{cleanSnippet(item.snippet)}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No evidence links found.</p>
      )}
    </section>
  )
}

export default EvidenceList
