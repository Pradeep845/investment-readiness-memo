function Catalysts({ items }) {
  return (
    <section className="card">
      <h2>Growth Catalysts</h2>
      {items?.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">No clear catalysts found yet.</p>
      )}
    </section>
  )
}

export default Catalysts
