import { useState } from 'react'
import { createCheckin, type MoodCheckinCreate } from '../api/checkins'
import { createManualSos, type SosCreateOptions } from '../api/sos'

interface BuddyOption {
  id: number
  name: string
  email: string
}

interface MoodCheckinFormProps {
  onSubmitted: () => void
  buddies: BuddyOption[]
  onSosCreated?: (alert: any) => void
}

const MOOD_OPTIONS = [
  { value: 1, label: '1 - Very low' },
  { value: 2, label: '2 - Low' },
  { value: 3, label: '3 - Okay' },
  { value: 4, label: '4 - Good' },
  { value: 5, label: '5 - Great' },
]

export function MoodCheckinForm({ onSubmitted, buddies, onSosCreated }: MoodCheckinFormProps) {
  const [moodScore, setMoodScore] = useState(3)
  const [tagsInput, setTagsInput] = useState('')
  const [note, setNote] = useState('')
  const [wantsCompany, setWantsCompany] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // SOS options
  const [sendSos, setSendSos] = useState(false)
  const [sosSeverity, setSosSeverity] = useState<'LOW' | 'MED' | 'HIGH'>('MED')
  const [broadcast, setBroadcast] = useState(false)
  const [selectedBuddyIds, setSelectedBuddyIds] = useState<Set<number>>(new Set())

  function toggleBuddy(id: number) {
    setSelectedBuddyIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSubmitting(true)
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/ea529403-4157-4bb2-8989-ab1b42396ecc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MoodCheckinForm.tsx:handleSubmit',message:'handleSubmit entry',data:{sendSos,moodScore,broadcast,selectedBuddyIdsSize:selectedBuddyIds.size,selectedBuddyIds:Array.from(selectedBuddyIds)},timestamp:Date.now(),hypothesisId:'H1'})}).catch(()=>{});
    // #endregion
    try {
      const tags = tagsInput
        .split(/[,\s]+/)
        .map((t) => t.trim())
        .filter(Boolean)
      const data: MoodCheckinCreate = {
        mood_score: moodScore,
        tags,
        note: note.trim() || undefined,
        wants_company: wantsCompany,
      }
      const checkin = await createCheckin(data)
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ea529403-4157-4bb2-8989-ab1b42396ecc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MoodCheckinForm.tsx:createCheckin',message:'createCheckin success',data:{checkinId:checkin.id},timestamp:Date.now(),hypothesisId:'H5'})}).catch(()=>{});
      // #endregion

      // If SOS is enabled, also send SOS
      if (sendSos) {
        const sosOptions: SosCreateOptions & { severity?: string } = {}
        if (broadcast) {
          sosOptions.broadcast = true
        } else if (selectedBuddyIds.size > 0) {
          sosOptions.buddy_ids = Array.from(selectedBuddyIds)
        }
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/ea529403-4157-4bb2-8989-ab1b42396ecc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MoodCheckinForm.tsx:createManualSos',message:'before createManualSos',data:{sosOptions:JSON.stringify(sosOptions),severity:sosSeverity},timestamp:Date.now(),hypothesisId:'H4'})}).catch(()=>{});
        // #endregion
        try {
          const alert = await createManualSos(sosSeverity, sosOptions)
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/ea529403-4157-4bb2-8989-ab1b42396ecc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MoodCheckinForm.tsx:createManualSos',message:'createManualSos success',data:{alertId:alert.id},timestamp:Date.now(),hypothesisId:'H1'})}).catch(()=>{});
          // #endregion
          onSosCreated?.(alert)
          setSuccess(`Check-in submitted + SOS #${alert.id} sent!`)
        } catch (err) {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/ea529403-4157-4bb2-8989-ab1b42396ecc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MoodCheckinForm.tsx:createManualSos',message:'createManualSos FAILED',data:{error:String(err)},timestamp:Date.now(),hypothesisId:'H1'})}).catch(()=>{});
          // #endregion
          setSuccess('Check-in submitted.')
          setError(err instanceof Error ? err.message : 'Check-in OK but SOS failed')
        }
      } else {
        setSuccess('Check-in submitted.')
      }

      setMoodScore(3)
      setTagsInput('')
      setNote('')
      setWantsCompany(false)
      setSendSos(false)
      setBroadcast(false)
      setSelectedBuddyIds(new Set())
      onSubmitted()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit check-in')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card mb-6">
      <h3 className="heading-sm mb-4">How are you feeling today?</h3>
      <div className="divider mb-4" />

      {error && (
        <div className="alert alert-danger mb-4 text-sm">{error}</div>
      )}
      {success && (
        <div className="alert alert-success mb-4 text-sm">{success}</div>
      )}

      <div className="flex-col gap-md">
        {/* Mood select */}
        <div className="input-group">
          <label>Mood (1-5)</label>
          <select
            className="select"
            value={moodScore}
            onChange={(e) => setMoodScore(Number(e.target.value))}
          >
            {MOOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Tags */}
        <div className="input-group">
          <label>Tags (comma-separated)</label>
          <input
            type="text"
            className="input"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="calm, hopeful, tired..."
          />
        </div>

        {/* Note */}
        <div className="input-group">
          <label>Note (optional)</label>
          <textarea
            className="textarea"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="How are you doing?"
            rows={3}
          />
        </div>

        {/* Company checkbox */}
        <label className="mood-company-checkbox">
          <input
            type="checkbox"
            checked={wantsCompany}
            onChange={(e) => setWantsCompany(e.target.checked)}
          />
          <span className="text-secondary text-sm">I'd like company today</span>
        </label>

        <div className="divider" />

        {/* SOS Section */}
        <div className="form-section">
          <label className="mood-company-checkbox" style={{ marginBottom: '0.5rem' }}>
            <input
              type="checkbox"
              checked={sendSos}
              onChange={(e) => setSendSos(e.target.checked)}
            />
            <span className="text-sm" style={{ fontWeight: 600 }}>Send SOS Alert with this check-in</span>
          </label>

          {sendSos && (
            <div className="flex-col gap-sm" style={{ marginTop: '0.75rem', paddingLeft: '0.5rem' }}>
              {/* Severity */}
              <div className="input-group">
                <label className="text-secondary text-sm">Severity</label>
                <div className="flex-center gap-sm mt-1">
                  {(['LOW', 'MED', 'HIGH'] as const).map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      className={`btn btn-sm ${
                        sosSeverity === sev
                          ? sev === 'HIGH'
                            ? 'btn-danger'
                            : sev === 'MED'
                            ? 'btn-secondary'
                            : 'btn-success'
                          : 'btn-ghost'
                      }`}
                      onClick={() => setSosSeverity(sev)}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              {/* Broadcast toggle */}
              <label className="mood-company-checkbox">
                <input
                  type="checkbox"
                  checked={broadcast}
                  onChange={(e) => {
                    setBroadcast(e.target.checked)
                    if (e.target.checked) setSelectedBuddyIds(new Set())
                  }}
                />
                <span className="text-secondary text-sm">Broadcast to all buddies</span>
              </label>

              {/* Buddy multi-select (only when not broadcasting) */}
              {!broadcast && buddies.length > 0 && (
                <div>
                  <span className="text-secondary text-sm" style={{ display: 'block', marginBottom: '0.4rem' }}>
                    Or select specific buddies:
                  </span>
                  <div className="flex-col gap-xs">
                    {buddies.map((b) => (
                      <label key={b.id} className="mood-company-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedBuddyIds.has(b.id)}
                          onChange={() => toggleBuddy(b.id)}
                        />
                        <span className="text-sm">{b.name} <span className="text-muted text-xs">({b.email})</span></span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {!broadcast && selectedBuddyIds.size === 0 && (
                <p className="text-muted text-xs">
                  No buddies selected — SOS will auto-select the best available buddies.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
        >
          {submitting ? 'Submitting...' : sendSos ? 'Submit Check-in + Send SOS' : 'Submit Check-in'}
        </button>
      </div>
    </form>
  )
}
