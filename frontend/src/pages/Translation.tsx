import { useEffect, useState } from 'react'
import { getMe } from '../api/auth'
import {
  getTranslateHistory,
  translateText,
  type TranslateHistoryItem,
  type TranslateResponse,
} from '../api/translate'
import { getToken } from '../state/authStore'

export default function Translation() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TranslateResponse | null>(null)
  const [history, setHistory] = useState<TranslateHistoryItem[]>([])
  const [userDisplayName, setUserDisplayName] = useState('You')

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

  useEffect(() => {
    async function loadUser() {
      let token: string | null = null
      try {
        token = getToken()
      } catch {
        return
      }
      if (!token) return
      try {
        const me = await getMe(token)
        if (me.full_name?.trim()) {
          setUserDisplayName(me.full_name.trim())
        }
      } catch {
        // keep default label
      }
    }
    loadUser()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await translateText({ message })
      setResult(data)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setLoading(false)
    }
  }

  function loadFromHistory(item: TranslateHistoryItem) {
    setMessage(item.question)
    setResult({
      empathetic_personalized_answer: item.response,
      safety_flag: item.safety_flag,
    })
  }

  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1 className="heading-lg">
          Chat with <span className="text-gradient">komradeAI</span>
        </h1>
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

        <button className="btn btn-primary" type="submit" disabled={loading || !message.trim()}>
          {loading ? 'Translating...' : 'Tell me!'}
        </button>

        {error && <p className="text-danger mt-3">{error}</p>}
      </form>

      <div className="card animate-in animate-in-delay-2" style={{ marginBottom: '1rem' }}>
        <h2 className="heading-sm mb-2">Empathetic Personalized Answer</h2>
        <p className="text-secondary">{result?.empathetic_personalized_answer ?? 'No output yet.'}</p>
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <span><strong>{userDisplayName}:</strong> {item.question}</span>
                  <span className="text-secondary text-sm"><strong>komradeAI:</strong> {item.response}</span>
                  <span className="text-muted text-xs">
                    {new Date(item.created_at).toLocaleString()} · {item.safety_flag}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
