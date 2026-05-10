function EvidenceList({ items }) {
  return (
    <section className="card full-width">
      <h2>Evidence</h2>
      {items?.length ? (
        <ul className="evidence-list">
          {items.map((item, index) => (
            <li key={`${item.url}-${index}`}>
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.title}
              </a>
              <p className="muted">{item.snippet || 'No snippet available.'}</p>
              <small>{item.source}</small>
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
