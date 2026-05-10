import { useMemo, useState } from 'react'
import './App.css'
import ScoreCard from './components/ScoreCard'
import RiskFlags from './components/RiskFlags'
import Catalysts from './components/Catalysts'
import StockTrend from './components/StockTrend'
import EvidenceList from './components/EvidenceList'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [form, setForm] = useState({
    company_name: '',
    website_url: '',
    ticker: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState(null)

  const loadingLabel = useMemo(() => {
    if (!loading) return ''
    return 'Collecting Anakin data, scoring investability, and preparing the report...'
  }, [loading])

  const updateField = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const onSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setReport(null)

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: form.company_name.trim(),
          website_url: form.website_url.trim(),
          ticker: form.ticker.trim() || null,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Request failed')
      }
      setReport(data)
    } catch (submitError) {
      setError(submitError.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header>
        <p className="eyebrow">Anakin-powered investing intelligence</p>
        <h1>VC Lens: Investability Copilot</h1>
        <p className="subtitle">
          Evaluate startups and public companies with transparent signals from website data, external
          research, and optional stock trend analysis.
        </p>
      </header>

      <form className="analyze-form" onSubmit={onSubmit}>
        <label>
          Company Name
          <input
            name="company_name"
            value={form.company_name}
            onChange={updateField}
            required
            placeholder="Acme Labs"
          />
        </label>
        <label>
          Company Website
          <input
            name="website_url"
            value={form.website_url}
            onChange={updateField}
            required
            placeholder="https://example.com"
          />
        </label>
        <label>
          Stock Ticker (optional)
          <input
            name="ticker"
            value={form.ticker}
            onChange={updateField}
            placeholder="AAPL"
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Run Investability Analysis'}
        </button>
      </form>

      {loading && <p className="status">{loadingLabel}</p>}
      {error && <p className="error">{error}</p>}

      {report && (
        <main className="report-grid">
          <ScoreCard score={report.score} confidence={report.confidence} summary={report.summary} />
          <RiskFlags items={report.risk_flags} />
          <Catalysts items={report.growth_catalysts} />
          <StockTrend data={report.stock_trend} />
          <EvidenceList items={report.evidence} />
        </main>
      )}
    </div>
  )
}

export default App
