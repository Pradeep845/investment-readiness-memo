import { useMemo, useState } from 'react'
import './App.css'
import ScoreCard from './components/ScoreCard'
import RiskFlags from './components/RiskFlags'
import Catalysts from './components/Catalysts'
import StockTrend from './components/StockTrend'
import EvidenceList from './components/EvidenceList'
import KeyFacts from './components/KeyFacts'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const log = (...args) => console.log('[IRM]', ...args)

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
    return 'Collecting public signals via Anakin and drafting your readiness memo...'
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

    const body = {
      company_name: form.company_name.trim(),
      website_url: form.website_url.trim(),
      ticker: form.ticker.trim() || null,
    }
    const started = performance.now()
    log('analyze_request_start', { api: API_BASE, body })

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const elapsedMs = Math.round(performance.now() - started)
      const rawText = await response.text()
      let data
      try {
        data = JSON.parse(rawText)
      } catch (parseErr) {
        log('analyze_response_not_json', {
          status: response.status,
          elapsedMs,
          snippet: rawText.slice(0, 400),
        })
        throw new Error(`Bad response (${response.status}): not JSON`)
      }

      log('analyze_response', {
        ok: response.ok,
        status: response.status,
        elapsedMs,
        diagnostics: data.diagnostics,
        score: data.score,
      })

      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        log('analyze_http_error', { status: response.status, detail })
        throw new Error(detail || 'Request failed')
      }
      setReport(data)
    } catch (submitError) {
      log('analyze_request_failed', {
        message: submitError.message,
        elapsedMs: Math.round(performance.now() - started),
      })
      setError(submitError.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header>
        <p className="eyebrow">Evidence-backed pre-investment brief</p>
        <h1>Investment Readiness Memo</h1>
        <p className="subtitle">
          Synthesize public footprint, external context, and optional market trend inputs into a single
          readiness view for startups and listed companies.
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
          {loading ? 'Drafting memo...' : 'Generate readiness memo'}
        </button>
      </form>

      {loading && <p className="status">{loadingLabel}</p>}
      {error && <p className="error">{error}</p>}

      {report && (
        <main className="report-grid">
          {report.diagnostics?.partial && (
            <section className="card full-width banner-warning">
              <strong>Partial memo.</strong> The {report.diagnostics.deadline_seconds || ''}s deadline was hit; phases still
              running were cancelled
              {Array.isArray(report.diagnostics.cancelled_phases) && report.diagnostics.cancelled_phases.length > 0
                ? ` (${report.diagnostics.cancelled_phases.join(', ')})`
                : ''}
              . Re-run for the full pipeline.
            </section>
          )}
          {report.diagnostics?.gemini_polished && (
            <section className="card full-width banner-info">
              Synthesized by Gemini using website, agentic research, and Wire signals.
            </section>
          )}
          <ScoreCard score={report.score} confidence={report.confidence} summary={report.summary} />
          <RiskFlags items={report.risk_flags} />
          <Catalysts items={report.growth_catalysts} />
          <StockTrend data={report.stock_trend} />
          <KeyFacts items={report.key_facts} />
          <EvidenceList items={report.evidence} />
          {report.diagnostics && Object.keys(report.diagnostics).length > 0 && (
            <section className="card full-width debug-panel">
              <details>
                <summary>Pipeline diagnostics (matches backend logs)</summary>
                <pre>{JSON.stringify(report.diagnostics, null, 2)}</pre>
              </details>
            </section>
          )}
        </main>
      )}
    </div>
  )
}

export default App
