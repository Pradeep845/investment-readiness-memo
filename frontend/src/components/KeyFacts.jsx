function KeyFacts({ items }) {
  if (!items || items.length === 0) return null
  return (
    <section className="card full-width">
      <h2>Key Facts</h2>
      <ul className="fact-list">
        {items.map((fact, idx) => (
          <li key={`fact-${idx}`}>{fact}</li>
        ))}
      </ul>
    </section>
  )
}

export default KeyFacts
