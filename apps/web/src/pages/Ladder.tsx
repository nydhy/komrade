import { useMemo, useState } from 'react'
import { generateLadder, type LadderResult, type LadderWeek } from '../api/ai'
import {
  completeLadderChallenge,
  getLatestLadderPlan,
  saveLadderPlan,
  type LadderPlan,
} from '../api/ladder'

export default function Ladder() {
  const [anxiety, setAnxiety] = useState(5)
  const [preferredTime, setPreferredTime] = useState('Evening')
  const [crowdTolerance, setCrowdTolerance] = useState('low')
  const [interests, setInterests] = useState('coffee, fitness')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generated, setGenerated] = useState<LadderResult | null>(null)
  const [plan, setPlan] = useState<LadderPlan | null>(null)

  const displayedChallenges = useMemo(() => {
    if (plan) return plan.challenges
    if (!generated) return []
    return generated.weeks.map((w) => ({
      id: `week-${w.week}`,
      week: w.week,
      title: w.title,
      difficulty: w.difficulty,
      rationale: w.rationale,
      suggested_time: w.suggested_time,
      status: 'generated',
      completed: false,
    }))
  }, [generated, plan])

  const xp = displayedChallenges.filter((c) => c.completed).length * 100
  const streak = (() => {
    const sorted = [...displayedChallenges].sort((a, b) => a.week - b.week)
    let count = 0
    for (const c of sorted) {
      if (c.completed) count += 1
      else break
    }
    return count
  })()

  async function onGenerate() {
    setError(null)
    setLoading(true)
    try {
      const intake = {
        anxiety_level: anxiety,
        preferred_time: preferredTime,
        crowd_tolerance: crowdTolerance,
        interests: interests.split(',').map((i) => i.trim()).filter(Boolean),
        lat: lat ? Number(lat) : null,
        lng: lng ? Number(lng) : null,
      }
      const data = await generateLadder(intake)
      setGenerated(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate ladder')
    } finally {
      setLoading(false)
    }
  }

  async function onSave() {
    if (!generated) return
    setError(null)
    setLoading(true)
    try {
      const data = await saveLadderPlan(generated.weeks as LadderWeek[])
      setPlan(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save plan')
    } finally {
      setLoading(false)
    }
  }

  async function onLoadLatest() {
    setError(null)
    setLoading(true)
    try {
      const data = await getLatestLadderPlan()
      setPlan(data)
      setGenerated(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No saved plan found')
    } finally {
      setLoading(false)
    }
  }

  async function onComplete(challengeId: string) {
    setError(null)
    setLoading(true)
    try {
      const data = await completeLadderChallenge(challengeId)
      setPlan(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete challenge')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1 className="heading-xl">Social Exposure Ladder</h1>
        <p className="text-secondary text-lg mt-2">Generate, save, and complete your 8-week plan.</p>
      </div>

      <section className="card mb-6 animate-in animate-in-delay-1">
        <div className="flex-between mb-4">
          <h2 className="heading-md">Intake</h2>
          <div className="text-sm text-secondary">XP: <strong>{xp}</strong> · Streak: <strong>{streak}</strong></div>
        </div>
        <div className="form-row">
          <div className="input-group">
            <label>Anxiety (1-10)</label>
            <input className="input" type="number" min={1} max={10} value={anxiety} onChange={(e) => setAnxiety(Number(e.target.value))} />
          </div>
          <div className="input-group">
            <label>Preferred time</label>
            <input className="input" value={preferredTime} onChange={(e) => setPreferredTime(e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="input-group">
            <label>Crowd tolerance</label>
            <select className="select" value={crowdTolerance} onChange={(e) => setCrowdTolerance(e.target.value)}>
              <option value="low">Low</option>
              <option value="med">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div className="input-group">
            <label>Interests (comma separated)</label>
            <input className="input" value={interests} onChange={(e) => setInterests(e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="input-group">
            <label>Latitude</label>
            <input className="input" value={lat} onChange={(e) => setLat(e.target.value)} />
          </div>
          <div className="input-group">
            <label>Longitude</label>
            <input className="input" value={lng} onChange={(e) => setLng(e.target.value)} />
          </div>
        </div>
        <div className="flex-center gap-sm mt-4" style={{ justifyContent: 'flex-start' }}>
          <button className="btn btn-primary" onClick={onGenerate} disabled={loading}>Generate Ladder</button>
          <button className="btn btn-secondary" onClick={onSave} disabled={loading || !generated}>Save Plan</button>
          <button className="btn btn-ghost" onClick={onLoadLatest} disabled={loading}>Load Latest</button>
        </div>
        {error && <div className="alert alert-danger mt-4">{error}</div>}
      </section>

      <section className="card animate-in animate-in-delay-2">
        <h2 className="heading-md mb-4">Weeks 1-8</h2>
        {displayedChallenges.length === 0 ? (
          <p className="text-muted text-sm">No ladder yet. Generate one to begin.</p>
        ) : (
          <div className="grid-2">
            {displayedChallenges.map((c) => (
              <article key={c.id} className="card card-hover">
                <div className="flex-between mb-2">
                  <span className="badge">Week {c.week}</span>
                  <span className="text-muted text-xs">{c.difficulty}</span>
                </div>
                <h3 className="heading-sm">{c.title}</h3>
                <p className="text-secondary text-sm mt-2">{c.rationale}</p>
                <p className="text-muted text-xs mt-2">Suggested: {c.suggested_time ?? 'Flexible'}</p>
                <div className="mt-3 flex-between">
                  <span className={`text-xs ${c.completed ? 'text-success' : 'text-muted'}`}>
                    {c.completed ? 'Completed' : c.status}
                  </span>
                  {plan && !c.completed && (
                    <button className="btn btn-sm btn-primary" onClick={() => onComplete(c.id)} disabled={loading}>
                      Complete
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

