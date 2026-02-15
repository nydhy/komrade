import { useEffect, useRef, useState } from 'react'
import {
  getTranslateHistory,
  transcribeAudio,
  translateText,
  type TranslateHistoryItem,
  type TranslateResponse,
} from '../api/translate'

const SUGGESTED_PROMPTS = [
  'I am feeling lonely',
  'Why is everybody mean',
  'I am disappointed with my life',
]

export default function Translation() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TranslateResponse | null>(null)
  const [history, setHistory] = useState<TranslateHistoryItem[]>([])
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

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
      const contextHistory = [...history]
        .reverse()
        .map((item) => ({
          user_message: item.question,
          komrade_ai_response: item.response,
          safety_flag: item.safety_flag,
          created_at: item.created_at,
        }))
      const data = await translateText({
        message,
        context: {
          chat_history: contextHistory,
        },
      })
      setResult(data)
      await loadHistory()
      setMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Translation failed')
    } finally {
      setLoading(false)
    }
  }

  async function startRecording() {
    setError(null)
    setMessage('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone is not supported in this browser.')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setError('Audio recording is not supported in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      streamRef.current = stream
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }

      recorder.onstop = async () => {
        setRecording(false)
        const streamValue = streamRef.current
        if (streamValue) {
          streamValue.getTracks().forEach((track) => track.stop())
          streamRef.current = null
        }

        if (chunksRef.current.length === 0) return
        const blobType = chunksRef.current[0]?.type || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: blobType })
        const extension = blobType.includes('wav') ? 'wav' : 'webm'
        const file = new File([blob], `recording.${extension}`, { type: blobType })

        setTranscribing(true)
        try {
          const transcript = await transcribeAudio(file)
          setMessage((prev) => (prev.trim() ? `${prev.trim()} ${transcript}` : transcript))
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Speech-to-text failed')
        } finally {
          setTranscribing(false)
          chunksRef.current = []
        }
      }

      recorder.start()
      setRecording(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not access microphone')
    }
  }

  function stopRecording() {
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    } else {
      setRecording(false)
    }
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
          <div className="flex-center gap-sm mt-3" style={{ justifyContent: 'flex-start', flexWrap: 'wrap' }}>
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setMessage(prompt)}
                disabled={loading || transcribing}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-center" style={{ gap: '0.75rem', justifyContent: 'flex-start' }}>
          <button
            className={`btn ${recording ? 'btn-danger' : 'btn-secondary'}`}
            type="button"
            onClick={recording ? stopRecording : startRecording}
            disabled={transcribing || loading}
          >
            {recording ? 'Stop recording' : transcribing ? 'Transcribing...' : 'Start recording'}
          </button>

          <button className="btn btn-primary" type="submit" disabled={loading || transcribing || !message.trim()}>
            {loading ? 'Replying...' : 'Tell me!'}
          </button>
        </div>

        {error && <p className="text-danger mt-3">{error}</p>}
      </form>

      <div className="card animate-in animate-in-delay-2" style={{ marginBottom: '1rem' }}>
        <h2 className="heading-sm mb-2">Personalized Answer</h2>
        <p className="text-secondary">{result?.empathetic_personalized_answer ?? 'No output yet.'}</p>
      </div>
    </div>
  )
}
