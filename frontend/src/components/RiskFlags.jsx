function RiskFlags({ items }) {
  return (
    <section className="card">
      <h2>Risk Flags</h2>
      {items?.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">No major red flags were detected in this pass.</p>
      )}
    </section>
  )
}

export default RiskFlags
