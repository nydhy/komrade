import { useEffect, useState } from 'react'
import {
  getTranslateHistory,
  translateText,
  type TranslateHistoryItem,
  type TranslateProvider,
  type TranslateResponse,
} from '../api/translate'

export default function Translation() {
  const [provider, setProvider] = useState<TranslateProvider>('ollama')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TranslateResponse | null>(null)
  const [history, setHistory] = useState<TranslateHistoryItem[]>([])

  async function loadHistory() {
    try {
      const data = await getTranslateHistory(10)
      setHistory(data)
    } catch {
      setHistory([])
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await translateText({ provider, message })
      setResult(data)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setLoading(false)
    }
  }

  function loadFromHistory(item: TranslateHistoryItem) {
    setMessage(item.message)
    setProvider(item.provider === 'gemini' ? 'gemini' : 'ollama')
    setResult({
      generic_answer: item.generic_answer,
      empathetic_personalized_answer: item.empathetic_personalized_answer,
      safety_flag: item.safety_flag,
    })
  }

  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1 className="heading-lg">Translation Layer</h1>
        <p className="text-secondary mt-2">Turn messages into generic + empathetic responses.</p>
      </div>

      <form onSubmit={handleSubmit} className="card animate-in animate-in-delay-1" style={{ marginBottom: '1rem' }}>
        <div className="input-group mb-4">
          <label>Message</label>
          <textarea
            className="textarea"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type text to translate..."
            required
          />
        </div>

        <div className="flex-center gap-sm" style={{ marginBottom: '1rem' }}>
          <button
            type="button"
            className={`btn btn-sm ${provider === 'ollama' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setProvider('ollama')}
          >
            Ollama
          </button>
          <button
            type="button"
            className={`btn btn-sm ${provider === 'gemini' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setProvider('gemini')}
          >
            Gemini
          </button>
        </div>

        <button className="btn btn-primary" type="submit" disabled={loading || !message.trim()}>
          {loading ? 'Translating...' : 'Translate'}
        </button>

        {error && <p className="text-danger mt-3">{error}</p>}
      </form>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        <div className="card animate-in animate-in-delay-2">
          <h2 className="heading-sm mb-2">Generic Answer</h2>
          <p className="text-secondary">{result?.generic_answer ?? 'No output yet.'}</p>
        </div>
        <div className="card animate-in animate-in-delay-2">
          <h2 className="heading-sm mb-2">Empathetic Personalized Answer</h2>
          <p className="text-secondary">{result?.empathetic_personalized_answer ?? 'No output yet.'}</p>
        </div>
      </div>

      <div className="card animate-in animate-in-delay-3">
        <h2 className="heading-sm mb-3">History</h2>
        {history.length === 0 ? (
          <p className="text-muted">No translation history yet.</p>
        ) : (
          <div className="flex-col gap-sm">
            {history.map((item, idx) => (
              <button
                key={`${item.created_at}-${idx}`}
                type="button"
                className="btn btn-ghost"
                style={{ textAlign: 'left', justifyContent: 'space-between' }}
                onClick={() => loadFromHistory(item)}
              >
                <span>{item.message}</span>
                <span className="text-muted text-xs">
                  {new Date(item.created_at).toLocaleString()} · {item.provider} · {item.safety_flag}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
