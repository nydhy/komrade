import { useState } from 'react'
import { translateContext, type TranslateResult } from '../api/ai'

export default function Translate() {
  const [message, setMessage] = useState('')
  const [context, setContext] = useState('{"goal":"civilian interview"}')
  const [result, setResult] = useState<TranslateResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onTranslate(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const ctx = context.trim() ? (JSON.parse(context) as Record<string, unknown>) : {}
      const data = await translateContext(message, ctx)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to translate')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container page-container-narrow">
      <div className="page-header animate-in">
        <h1 className="heading-xl">Translation Layer</h1>
        <p className="text-secondary text-lg mt-2">Military-to-civilian response helper.</p>
      </div>

      <form className="card animate-in animate-in-delay-1" onSubmit={onTranslate}>
        <div className="input-group mb-4">
          <label>Message</label>
          <textarea
            className="textarea"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe the military experience to translate..."
            required
          />
        </div>
        <div className="input-group mb-4">
          <label>Context JSON (optional)</label>
          <textarea
            className="textarea"
            rows={3}
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" disabled={loading} type="submit">
          {loading ? 'Translating...' : 'Translate'}
        </button>
      </form>

      {error && <div className="alert alert-danger mt-4">{error}</div>}

      {result && (
        <section className="card mt-4 animate-in animate-in-delay-2">
          <div className="badge mb-2">Safety: {result.safety_flag}</div>
          <h2 className="heading-md mb-2">Generic Answer</h2>
          <p className="text-secondary mb-4">{result.generic_answer}</p>
          <h2 className="heading-md mb-2">Empathetic Personalized Answer</h2>
          <p className="text-secondary">{result.empathetic_personalized_answer}</p>
        </section>
      )}
    </div>
  )
}

