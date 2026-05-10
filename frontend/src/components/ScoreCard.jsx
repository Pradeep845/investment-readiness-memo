function ScoreCard({ score, confidence, summary }) {
  const grade = score >= 75 ? 'Strong' : score >= 55 ? 'Moderate' : 'Cautious'

  return (
    <section className="card">
      <h2>Readiness score</h2>
      <p className="score">{score}/100</p>
      <p className="pill">{grade} conviction</p>
      <p className="muted">Confidence: {confidence}</p>
      <p>{summary}</p>
    </section>
  )
}

export default ScoreCard
