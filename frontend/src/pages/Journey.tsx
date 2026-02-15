import { useEffect, useMemo, useState } from 'react'
import {
  generateJourneyChallenges,
  getJourneyChallengeInsights,
  getJourneyProgress,
  saveJourneyProgress,
  type JourneyChallenge,
  type JourneyChallengeInsights,
  type JourneyProgressResponse,
} from '../api/journey'
import '../styles/journey-k1.css'

type Screen = 'intake' | 'loading' | 'ladder'
type Feeling = 'crushed' | 'made_it' | 'adjusted' | 'not_ready'
type NextAction = 'next' | 'repeat' | 'adjust'

type OptionItem = { id: string; title: string; subtitle: string }

const TRIGGER_CHIPS = [
  'Loud noises',
  'Crowds',
  'Small talk',
  'Being looked at',
  'Unpredictable situations',
  'Questions about service',
  'Feeling trapped',
  'Explaining gaps',
]

const INTEREST_CHIPS = [
  'Coffee',
  'Fitness/Gym',
  'Reading',
  'Gaming',
  'Sports (playing)',
  'Sports (watching)',
  'Outdoors/Hiking',
  'Cars/Motorcycles',
  'Music',
  'Cooking',
  'Tech',
  'Art/Crafts',
]

const PAST_COMFORT_OPTIONS: OptionItem[] = [
  { id: 'month', title: 'Within the last month', subtitle: 'Recent struggle, looking to rebuild' },
  { id: '3_6_months', title: '3-6 months ago', subtitle: 'Been avoiding for a while' },
  { id: '6_plus', title: '6+ months ago', subtitle: "It's been a long time" },
  { id: 'pre_deploy', title: 'Since before deployment', subtitle: 'Civilian life feels completely foreign' },
]

const GOAL_OPTIONS: OptionItem[] = [
  { id: 'leave_house', title: 'Just leaving the house regularly', subtitle: 'Small steps are still progress' },
  { id: 'public_alone', title: 'Going to public places alone', subtitle: 'Coffee shops, stores, etc.' },
  { id: 'conversations', title: 'Having conversations with strangers', subtitle: 'Rebuilding social skills' },
  { id: 'groups', title: 'Joining groups or activities', subtitle: 'Finding a community again' },
  { id: 'events', title: 'Attending events (networking, social)', subtitle: 'Professional/personal reintegration' },
]

const SUPPORT_OPTIONS: OptionItem[] = [
  { id: 'yes', title: 'Yes, I have someone', subtitle: 'Can bring backup if needed' },
  {
    id: 'open_komrades',
    title: 'Not really, but open to meeting Komrades',
    subtitle: 'Would connect with peer support',
  },
  { id: 'solo', title: 'Prefer to do this solo for now', subtitle: 'Want to prove it to myself first' },
]

function fmtDate(iso: string | null): string {
  if (!iso) return 'Completed'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'Completed'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function difficultyLabel(value: string): string {
  const v = value.toUpperCase()
  if (v === 'EASY') return '🟢 Quiet & Solo'
  if (v === 'MEDIUM') return '🟡 Small Groups'
  if (v === 'HARD') return '🔴 Extended Social'
  return v
}

function shortTitle(title: string, max = 50): string {
  const clean = title.trim()
  if (clean.length <= max) return clean
  return `${clean.slice(0, max).trim()}...`
}

function compactText(text: string | null | undefined, max = 180): string {
  const clean = (text ?? '').replace(/\s+/g, ' ').trim()
  if (!clean) return 'Steady progress through consistent, low-pressure reps.'
  if (clean.length <= max) return clean
  return `${clean.slice(0, max).trim()}...`
}

export default function Journey() {
  const [screen, setScreen] = useState<Screen>('intake')
  const [loadingInit, setLoadingInit] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [anxietyLevel, setAnxietyLevel] = useState(7)
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>(['Small talk'])
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Coffee'])
  const [pastComfort, setPastComfort] = useState('3_6_months')
  const [goal, setGoal] = useState('conversations')
  const [supportMode, setSupportMode] = useState('solo')
  const [avoidanceText, setAvoidanceText] = useState('')

  const [challenges, setChallenges] = useState<JourneyChallenge[]>([])
  const [activeChallengeId, setActiveChallengeId] = useState<number | null>(null)
  const [xp, setXp] = useState(0)
  const [level, setLevel] = useState(1)
  const [streak, setStreak] = useState(0)

  const [showCompletionModal, setShowCompletionModal] = useState(false)
  const [showViewDetailsModal, setShowViewDetailsModal] = useState(false)
  const [showTellMeMoreModal, setShowTellMeMoreModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [selectedChallengeId, setSelectedChallengeId] = useState<number | null>(null)
  const [insightsByChallengeId, setInsightsByChallengeId] = useState<Record<number, JourneyChallengeInsights>>({})
  const [loadingInsights, setLoadingInsights] = useState(false)

  const [completionFeeling, setCompletionFeeling] = useState<Feeling>('made_it')
  const [nextAction, setNextAction] = useState<NextAction>('next')
  const [previewNumber, setPreviewNumber] = useState(4)

  const [toastMessage, setToastMessage] = useState('Marked for practice')
  const [toastVisible, setToastVisible] = useState(false)

  const completedChallenges = useMemo(
    () => challenges.filter((c) => c.is_completed).sort((a, b) => a.sort_order - b.sort_order),
    [challenges],
  )

  const orderedChallenges = useMemo(
    () => [...challenges].sort((a, b) => a.sort_order - b.sort_order),
    [challenges],
  )

  const currentChallenge = useMemo(
    () => orderedChallenges.find((c) => !c.is_completed) ?? null,
    [orderedChallenges],
  )

  const selectedChallenge = useMemo(
    () => orderedChallenges.find((c) => c.id === selectedChallengeId) ?? null,
    [orderedChallenges, selectedChallengeId],
  )

  const selectedInsights = useMemo(
    () => (selectedChallengeId ? insightsByChallengeId[selectedChallengeId] ?? null : null),
    [insightsByChallengeId, selectedChallengeId],
  )

  const attemptedCount = useMemo(
    () => orderedChallenges.filter((c) => c.is_completed || c.id === activeChallengeId).length,
    [orderedChallenges, activeChallengeId],
  )

  const xpProgressPercent = useMemo(() => {
    const xpInLevel = xp - (Math.max(1, level) - 1) * 100
    return Math.max(0, Math.min(100, xpInLevel))
  }, [xp, level])
  const xpInLevel = useMemo(() => xp - (Math.max(1, level) - 1) * 100, [xp, level])

  const nextChallengeNumber = useMemo(() => {
    if (!currentChallenge) return completedChallenges.length + 1
    return getChallengeNumber(currentChallenge) + 1
  }, [currentChallenge, completedChallenges.length, orderedChallenges])

  const activeIndex = useMemo(() => {
    const idx = orderedChallenges.findIndex((c) => !c.is_completed)
    return idx >= 0 ? idx : Math.max(0, orderedChallenges.length - 1)
  }, [orderedChallenges])

  const visibleChallenges = useMemo(() => {
    const startIndex = Math.max(0, activeIndex - 2)
    return orderedChallenges.slice(startIndex, startIndex + 5)
  }, [orderedChallenges, activeIndex])

  const visibleCompleted = useMemo(
    () => visibleChallenges.filter((c) => c.is_completed),
    [visibleChallenges],
  )
  const visibleCurrent = useMemo(
    () => visibleChallenges.find((c) => !c.is_completed) ?? null,
    [visibleChallenges],
  )
  const visibleLocked = useMemo(
    () => visibleChallenges.filter((c) => !c.is_completed && c.id !== visibleCurrent?.id),
    [visibleChallenges, visibleCurrent],
  )

  const lockedDisplayItems = useMemo(() => {
    const items = [...visibleLocked]
    const needed = Math.max(0, 2 - items.length)
    let nextNumber = orderedChallenges.length + 1
    for (let i = 0; i < needed; i += 1) {
      items.push({
        id: -1 * (i + 1),
        title: 'Next Challenge',
        description: null,
        difficulty: 'MEDIUM',
        xp_reward: 0,
        is_completed: false,
        sort_order: nextNumber,
        created_at: '',
        completed_at: null,
        challenge_number: nextNumber,
      })
      nextNumber += 1
    }
    return items.slice(0, 2)
  }, [visibleLocked, orderedChallenges.length])

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoadingInit(true)
      setError(null)
      try {
        const data = await getJourneyProgress()
        if (!mounted) return
        hydrate(data)
      } catch (err) {
        if (!mounted) return
        setError(err instanceof Error ? err.message : 'Failed to load journey')
      } finally {
        if (mounted) setLoadingInit(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [])

  function hydrate(data: JourneyProgressResponse) {
    const sorted = [...data.challenges].sort((a, b) => a.sort_order - b.sort_order)
    setChallenges(sorted)
    setActiveChallengeId(data.progress.active_challenge_id)
    setXp(data.progress.xp_total)
    setLevel(data.progress.level)
    setStreak(data.progress.current_streak)
    setAvoidanceText((data.progress.avoidance_list || []).join(', '))
    setScreen(sorted.length > 0 ? 'ladder' : 'intake')
  }

  function showToast(message: string) {
    setToastMessage(message)
    setToastVisible(true)
    window.setTimeout(() => setToastVisible(false), 2500)
  }

  function toggleChip(value: string, selected: string[], setSelected: (v: string[]) => void) {
    if (selected.includes(value)) {
      setSelected(selected.filter((v) => v !== value))
      return
    }
    setSelected([...selected, value])
  }

  function parseAvoidance(value: string): string[] {
    return value
      .split(/[\n,]/g)
      .map((v) => v.trim())
      .filter(Boolean)
  }

  async function generateJourney() {
    setError(null)
    setScreen('loading')
    try {
      await generateJourneyChallenges({
        anxiety_level: anxietyLevel,
        interests: selectedInterests.length ? selectedInterests : ['Coffee'],
        triggers: selectedTriggers,
        time_since_comfortable: PAST_COMFORT_OPTIONS.find((o) => o.id === pastComfort)?.title ?? pastComfort,
        end_goal: GOAL_OPTIONS.find((o) => o.id === goal)?.title ?? goal,
        energy_times: ['Whenever works for you'],
        location: 'your area',
        avoid_situations: avoidanceText.trim() || 'none specified',
        challenge_count: 5,
      })
      const data = await getJourneyProgress()
      hydrate(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate journey')
      setScreen(challenges.length > 0 ? 'ladder' : 'intake')
    }
  }

  async function saveCompletion() {
    if (!currentChallenge) return
    setSaving(true)
    setError(null)
    try {
      const completed = completionFeeling !== 'not_ready' && nextAction !== 'repeat'
      const payload = {
        challenge_id: currentChallenge.id,
        completed,
        xp_earned: completed ? currentChallenge.xp_reward : 0,
        current_feeling: completionFeeling,
        next_step: nextAction,
        avoidance_list: parseAvoidance(avoidanceText),
      }
      const data = await saveJourneyProgress(payload)
      hydrate(data)
      setShowCompletionModal(false)
      showToast('Progress saved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save progress')
    } finally {
      setSaving(false)
    }
  }

  async function practiceAgain(challengeId: number) {
    setSaving(true)
    setError(null)
    try {
      const data = await saveJourneyProgress({
        challenge_id: challengeId,
        completed: false,
        xp_earned: 0,
        current_feeling: completionFeeling,
        next_step: 'repeat',
        avoidance_list: parseAvoidance(avoidanceText),
      })
      hydrate(data)
      showToast('✓ Marked for practice')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update challenge')
    } finally {
      setSaving(false)
    }
  }

  async function loadChallengeInsights(challengeId: number) {
    if (insightsByChallengeId[challengeId]) return
    setLoadingInsights(true)
    setError(null)
    try {
      const insights = await getJourneyChallengeInsights(challengeId)
      setInsightsByChallengeId((prev) => ({ ...prev, [challengeId]: insights }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load challenge details')
    } finally {
      setLoadingInsights(false)
    }
  }

  function getChallengeNumber(challenge: JourneyChallenge): number {
    const idx = orderedChallenges.findIndex((c) => c.id === challenge.id)
    return idx >= 0 ? idx + 1 : challenge.sort_order
  }

  return (
    <div className="journey-k1">
      <div className={`toast ${toastVisible ? 'show' : ''}`}>
        <span className="toast-icon">✓</span>
        <span className="toast-text">{toastMessage}</span>
      </div>

      {error && <div className="journey-error">{error}</div>}

      <div className={`screen ${screen === 'intake' ? 'active' : ''}`}>
        <div className="container">
          <div className="header">
            <h1>Let&apos;s Build Your Journey</h1>
            <p>Take your time. These questions help us create a plan that works for YOU, at YOUR pace.</p>
          </div>

          <div className="progress-indicator">
            <div className="progress-fill" style={{ width: '20%' }} />
          </div>

          <div className="section">
            <div className="section-title">How are you feeling right now?</div>
            <p className="section-subtitle">Honest answers only - this is a judgment-free zone</p>

            <div className="question">
              <label className="question-label">When you think about being in public spaces, how do you feel?</label>
              <p className="question-helper">1 = comfortable, 10 = overwhelming anxiety</p>
              <div className="slider-container">
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={anxietyLevel}
                  className="slider"
                  onChange={(e) => setAnxietyLevel(Number(e.target.value))}
                />
                <div className="slider-labels">
                  <span>Comfortable</span>
                  <span>Manageable</span>
                  <span>Overwhelming</span>
                </div>
                <div className="slider-value">{anxietyLevel}</div>
              </div>
            </div>

            <div className="question">
              <label className="question-label">What makes social situations hardest for you?</label>
              <p className="question-helper">Select all that apply - understanding your triggers helps us start easier</p>
              <div className="chips-container">
                {TRIGGER_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    className={`chip ${selectedTriggers.includes(chip) ? 'selected' : ''}`}
                    onClick={() => toggleChip(chip, selectedTriggers, setSelectedTriggers)}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            <div className="question">
              <label className="question-label">How long has it been since you felt comfortable in a social setting?</label>
              <div className="options">
                {PAST_COMFORT_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`option ${pastComfort === opt.id ? 'selected' : ''}`}
                    onClick={() => setPastComfort(opt.id)}
                  >
                    <div className="option-radio" />
                    <div className="option-text">
                      <div className="option-title">{opt.title}</div>
                      <div className="option-subtitle">{opt.subtitle}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="section">
            <div className="section-title">What does success look like for you?</div>
            <p className="section-subtitle">No pressure - these are YOUR goals, not ours</p>

            <div className="question">
              <label className="question-label">In 2-3 months, what would feel like a win?</label>
              <p className="question-helper">Help us understand where you want to be</p>
              <div className="options">
                {GOAL_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`option ${goal === opt.id ? 'selected' : ''}`}
                    onClick={() => setGoal(opt.id)}
                  >
                    <div className="option-radio" />
                    <div className="option-text">
                      <div className="option-title">{opt.title}</div>
                      <div className="option-subtitle">{opt.subtitle}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="question">
              <label className="question-label">What interests or hobbies did you used to enjoy?</label>
              <p className="question-helper">We&apos;ll build challenges around things you actually care about</p>
              <div className="chips-container">
                {INTEREST_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    className={`chip ${selectedInterests.includes(chip) ? 'selected' : ''}`}
                    onClick={() => toggleChip(chip, selectedInterests, setSelectedInterests)}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="section">
            <div className="section-title">Building your safety net</div>
            <p className="section-subtitle">Knowing you have backup makes trying easier</p>

            <div className="info-box">
              <span className="info-icon">🤝</span>
              <div className="info-text">
                <strong>Why we ask:</strong> Challenges are easier when you know someone has your six.
              </div>
            </div>

            <div className="question">
              <label className="question-label">Do you have someone who could join you for challenges if needed?</label>
              <p className="question-helper">Battle buddy, friend, family - anyone you trust</p>
              <div className="options">
                {SUPPORT_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`option ${supportMode === opt.id ? 'selected' : ''}`}
                    onClick={() => setSupportMode(opt.id)}
                  >
                    <div className="option-radio" />
                    <div className="option-text">
                      <div className="option-title">{opt.title}</div>
                      <div className="option-subtitle">{opt.subtitle}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="question">
              <label className="question-label">Are there any specific situations we should avoid right now?</label>
              <p className="question-helper">Optional - helps us not suggest triggering scenarios</p>
              <textarea
                value={avoidanceText}
                onChange={(e) => setAvoidanceText(e.target.value)}
                placeholder="Example: Avoid bars or anywhere with alcohol"
              />
            </div>
          </div>

          <div className="button-group">
            <button type="button" className="btn btn-secondary">Save for Later</button>
            <button type="button" className="btn btn-primary" onClick={generateJourney} disabled={loadingInit || saving}>
              Generate My Journey
            </button>
          </div>
        </div>
      </div>

      <div className={`screen ${screen === 'loading' ? 'active' : ''}`}>
        <div className="container">
          <div className="loading-content">
            <div className="loading-spinner" />
            <div className="loading-text">Creating your personalized journey...</div>
            <div className="loading-subtext">Building challenges tailored to your pace and goals</div>
          </div>
        </div>
      </div>

      <div className={`screen ${screen === 'ladder' ? 'active' : ''}`}>
        <div className="container">
          <div className="header">
            <h1>Your Journey</h1>
            <p>Your pace, your journey. No pressure, just progress.</p>
          </div>

          <div className="progress-card">
            <div className="progress-header">
              <span className="level-badge">Level {level}</span>
              <span className="xp-count">{xp} XP</span>
            </div>
            <div className="xp-progress-bar">
              <div className="xp-progress-fill" style={{ width: `${xpProgressPercent}%` }} />
            </div>
            <p className="xp-next-level">{Math.max(0, xpInLevel)} / 100 XP to Level {level + 1}</p>
            <div className="stats-grid">
              <div className="stat">
                <div className="stat-value">{streak}</div>
                <div className="stat-label">Days showing up</div>
              </div>
              <div className="stat">
                <div className="stat-value">{attemptedCount}</div>
                <div className="stat-label">Challenges attempted</div>
              </div>
              <div className="stat">
                <div className="stat-value">{completedChallenges.length}</div>
                <div className="stat-label">Milestones reached</div>
              </div>
            </div>
            <div className="encouragement">💪 You&apos;re building the habit. We believe in you.</div>
          </div>

          <div className="challenges-container">
            {visibleCompleted.map((c) => (
              <div key={c.id} className="challenge-card completed">
                <div className="challenge-header">
                  <span className="challenge-number">Challenge {getChallengeNumber(c)}</span>
                  <div className="challenge-badges">
                    <span className="badge badge-quiet">{difficultyLabel(c.difficulty)}</span>
                  </div>
                </div>
                <h3 className="challenge-title">{shortTitle(c.title)}</h3>
                <div className="challenge-completion">
                  <span>✓</span>
                  <span>Completed {fmtDate(c.completed_at)} • Made it through 💪</span>
                </div>
                <div className="challenge-description">
                  <div className="challenge-description-title">What you built:</div>
                  <div className="challenge-description-text">{compactText(c.what_this_builds)}</div>
                </div>
                {((c.recommended_times?.length ?? 0) > 0 || (c.suggested_locations?.length ?? 0) > 0) && (
                  <div className="completed-meta-grid">
                    {(c.recommended_times?.length ?? 0) > 0 && (
                      <div className="completed-meta-item">
                        <div className="completed-meta-label">Best times</div>
                        <div className="completed-meta-value">{c.recommended_times?.slice(0, 2).join(' • ')}</div>
                      </div>
                    )}
                    {(c.suggested_locations?.length ?? 0) > 0 && (
                      <div className="completed-meta-item">
                        <div className="completed-meta-label">Suggestions used</div>
                        <div className="completed-meta-value">{c.suggested_locations?.slice(0, 2).join(' • ')}</div>
                      </div>
                    )}
                  </div>
                )}
                <div className="challenge-actions">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setSelectedChallengeId(c.id)
                      setShowViewDetailsModal(true)
                      void loadChallengeInsights(c.id)
                    }}
                  >
                    View Details
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => practiceAgain(c.id)} disabled={saving}>Practice Again</button>
                </div>
              </div>
            ))}

            {visibleCurrent && (
              <div className="challenge-card current">
                <div className="challenge-header">
                  <span className="challenge-number">Challenge {getChallengeNumber(visibleCurrent)} • Ready When You Are</span>
                  <div className="challenge-badges">
                    <span className="badge badge-quiet">{difficultyLabel(visibleCurrent.difficulty)}</span>
                  </div>
                </div>
                <h3 className="challenge-title">{shortTitle(visibleCurrent.title)}</h3>

                <div className="challenge-details">
                  <div className="detail-section">
                    <div className="detail-label">⏱️ Duration</div>
                    <p className="detail-value">{visibleCurrent.duration ?? '10-20 minutes (adjust as needed)'}</p>
                  </div>

                  {visibleCurrent.recommended_times && visibleCurrent.recommended_times.length > 0 && (
                    <div className="detail-section">
                      <div className="detail-label">🕐 Best Times</div>
                      <ul className="suggestion-list">
                        {visibleCurrent.recommended_times.map((time, idx) => (
                          <li key={`${visibleCurrent.id}-time-${idx}`}>{time}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {visibleCurrent.suggested_locations && visibleCurrent.suggested_locations.length > 0 && (
                    <div className="detail-section">
                      <div className="detail-label">📍 Suggestions</div>
                      <ul className="suggestion-list">
                        {visibleCurrent.suggested_locations.slice(0, 3).map((loc, idx) => (
                          <li key={`${visibleCurrent.id}-loc-${idx}`}>{loc}</li>
                        ))}
                      </ul>
                      {visibleCurrent.suggested_locations.length > 3 && (
                        <p className="more-options">+ more in "Tell Me More"</p>
                      )}
                    </div>
                  )}

                  <div className="detail-section">
                    <div className="detail-label">💬 Interaction</div>
                    <p className="detail-value">{visibleCurrent.interaction_required ?? 'None required - just be present.'}</p>
                  </div>

                  {visibleCurrent.you_can_also && visibleCurrent.you_can_also.length > 0 && (
                    <div className="detail-section">
                      <div className="detail-label">✨ You Can Also</div>
                      <ul className="suggestion-list">
                        {visibleCurrent.you_can_also.map((option, idx) => (
                          <li key={`${visibleCurrent.id}-also-${idx}`}>{option}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="challenge-description">
                  <div className="challenge-description-title">What this builds:</div>
                  <div className="challenge-description-text">{visibleCurrent.what_this_builds ?? 'Low-pressure social reps and consistency.'}</div>
                </div>

                <div className="challenge-description">
                  <div className="challenge-description-title">Exit strategy:</div>
                  <div className="challenge-description-text">{visibleCurrent.exit_strategy ?? 'If it feels awkward, that&apos;s normal. You can leave right after.'}</div>
                </div>

                <div className="challenge-actions">
                  <button type="button" className="btn btn-primary" onClick={() => setShowCompletionModal(true)}>How did it go?</button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setSelectedChallengeId(visibleCurrent.id)
                      setShowTellMeMoreModal(true)
                      void loadChallengeInsights(visibleCurrent.id)
                    }}
                  >
                    Tell Me More
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="locked-challenges-grid">
            {lockedDisplayItems.map((challenge) => {
              const n = challenge.challenge_number ?? challenge.sort_order
              return (
              <div key={`locked-${challenge.id}-${n}`} className="locked-challenge-card">
                <div className="locked-challenge-header">
                  <div className="locked-challenge-number">Challenge {n}</div>
                  <div className="locked-challenge-title">Next Challenge</div>
                  <div className="locked-challenge-badge"><span className="badge badge-small">🟡 Small Groups</span></div>
                </div>
                <div className="lock-icon">🔒</div>
                <div className="lock-text">Unlocks after Challenge {n - 1}</div>
                <button
                  type="button"
                  className="btn btn-secondary preview-btn"
                  onClick={() => {
                    setPreviewNumber(n)
                    setShowPreviewModal(true)
                  }}
                >
                  Preview
                </button>
              </div>
            )})}
          </div>

          <div className="future-counter">
            <div className="future-counter-icon">🎯</div>
            <div className="future-counter-text">More milestones ahead<br />We&apos;ll introduce them when you&apos;re ready</div>
          </div>
        </div>
      </div>

      <div className={`modal-overlay ${showCompletionModal ? 'active' : ''}`} onClick={() => setShowCompletionModal(false)}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>Challenge {currentChallenge ? getChallengeNumber(currentChallenge) : 0}: How did it go?</h2>
          <p className="modal-subtitle">Honest answer - this is just for you. No judgment.</p>

          <div className="option-group">
            <span className="option-label">How do you feel?</span>
            <div className="options">
              <button type="button" className={`option completion-feeling ${completionFeeling === 'crushed' ? 'selected' : ''}`} onClick={() => setCompletionFeeling('crushed')}>
                <span className="option-emoji">🔥</span><div className="option-text"><div className="option-title">Crushed it</div><div className="option-subtitle">Felt confident, conversation flowed</div></div>
              </button>
              <button type="button" className={`option completion-feeling ${completionFeeling === 'made_it' ? 'selected' : ''}`} onClick={() => setCompletionFeeling('made_it')}>
                <span className="option-emoji">💪</span><div className="option-text"><div className="option-title">Made it through</div><div className="option-subtitle">Was awkward, but I did it</div></div>
              </button>
              <button type="button" className={`option completion-feeling ${completionFeeling === 'adjusted' ? 'selected' : ''}`} onClick={() => setCompletionFeeling('adjusted')}>
                <span className="option-emoji">🤝</span><div className="option-text"><div className="option-title">Tried but adjusted</div><div className="option-subtitle">Modified the challenge, still showing up</div></div>
              </button>
              <button type="button" className={`option completion-feeling ${completionFeeling === 'not_ready' ? 'selected' : ''}`} onClick={() => setCompletionFeeling('not_ready')}>
                <span className="option-emoji">🌙</span><div className="option-text"><div className="option-title">Wasn&apos;t ready today</div><div className="option-subtitle">That&apos;s okay, tomorrow&apos;s a new day</div></div>
              </button>
            </div>
          </div>

          <div className="option-group">
            <span className="option-label">What&apos;s next?</span>
            <div className="options">
              <button type="button" className={`option next-action ${nextAction === 'next' ? 'selected' : ''}`} onClick={() => setNextAction('next')}>
                <span className="option-emoji">→</span><div className="option-text"><div className="option-title">Ready for Challenge {nextChallengeNumber}</div><div className="option-subtitle">Unlock the next challenge</div></div>
              </button>
              <button type="button" className={`option next-action ${nextAction === 'repeat' ? 'selected' : ''}`} onClick={() => setNextAction('repeat')}>
                <span className="option-emoji">↻</span><div className="option-text"><div className="option-title">Practice this again</div><div className="option-subtitle">Build more confidence first</div></div>
              </button>
              <button type="button" className={`option next-action ${nextAction === 'adjust' ? 'selected' : ''}`} onClick={() => setNextAction('adjust')}>
                <span className="option-emoji">⚙️</span><div className="option-text"><div className="option-title">Adjust my journey</div><div className="option-subtitle">This pace isn&apos;t quite right</div></div>
              </button>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" style={{ flex: 0.3 }} onClick={() => setShowCompletionModal(false)}>Cancel</button>
            <button type="button" className="btn btn-primary" onClick={saveCompletion} disabled={saving}>{saving ? 'Saving...' : 'Save Progress'}</button>
          </div>
        </div>
      </div>

      <div className={`modal-overlay ${showViewDetailsModal ? 'active' : ''}`} onClick={() => setShowViewDetailsModal(false)}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>Challenge {selectedChallenge ? getChallengeNumber(selectedChallenge) : 0}: {selectedChallenge?.title ?? 'Details'}</h2>
          <p className="modal-subtitle">{selectedChallenge ? difficultyLabel(selectedChallenge.difficulty) : 'Challenge Details'}</p>
          <div className="detail-section">
            <h3>Your Success Timeline</h3>
            {!selectedInsights && (
              <>
                <div className="timeline-item">
                  <span className="timeline-date">{fmtDate(selectedChallenge?.created_at ?? null)}</span>
                  <span className="timeline-feeling">Challenge created</span>
                  <span className="timeline-xp">+0 XP</span>
                </div>
                {selectedChallenge?.is_completed && (
                  <div className="timeline-item">
                    <span className="timeline-date">{fmtDate(selectedChallenge.completed_at)}</span>
                    <span className="timeline-feeling">Completed and logged</span>
                    <span className="timeline-xp">+{selectedChallenge.xp_reward} XP</span>
                  </div>
                )}
              </>
            )}
            {selectedInsights?.success_timeline.map((item, idx) => (
              <div key={`${item.date_label}-${idx}`} className="timeline-item">
                <span className="timeline-date">{item.date_label}</span>
                <span className="timeline-feeling">{item.feeling}</span>
                <span className="timeline-xp">+{item.xp} XP</span>
              </div>
            ))}
          </div>
          <div className="detail-section">
            <h3>What You Built</h3>
            {(
              selectedInsights?.what_you_built?.length
                ? selectedInsights.what_you_built
                : [
                    selectedChallenge?.what_this_builds ?? 'Consistent exposure and confidence building in real-world settings.',
                    selectedChallenge?.why_this_works ?? 'Small, repeatable reps help build confidence over time.',
                  ]
            ).map((line, idx) => (
              <p key={`built-${idx}`}>{line}</p>
            ))}
          </div>
          <div className="detail-section">
            <h3>Exit Strategy</h3>
            <p>{selectedChallenge?.exit_strategy ?? selectedInsights?.modification_easier ?? 'You can pause and leave at any point. Leaving early still counts as progress.'}</p>
          </div>
          <div className="detail-section">
            <h3>Your Memories</h3>
            <p style={{ fontStyle: 'italic', color: '#9CA3AF' }}>
              {selectedInsights?.memory_quote
                ? selectedInsights.memory_quote
                : selectedChallenge?.is_completed
                  ? `Completed on ${fmtDate(selectedChallenge.completed_at)}.`
                  : 'Complete this challenge to add a reflection entry.'}
            </p>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setShowViewDetailsModal(false)}>Close</button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                if (selectedChallenge) {
                  void practiceAgain(selectedChallenge.id)
                }
                setShowViewDetailsModal(false)
              }}
            >
              Practice Again
            </button>
          </div>
        </div>
      </div>

      <div className={`modal-overlay ${showTellMeMoreModal ? 'active' : ''}`} onClick={() => setShowTellMeMoreModal(false)}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>
            Challenge {selectedChallenge ? getChallengeNumber(selectedChallenge) : 0}: {selectedChallenge?.title ?? 'Brief small talk'}
          </h2>
          <p className="modal-subtitle">{selectedChallenge ? difficultyLabel(selectedChallenge.difficulty) : 'Challenge Details'}</p>
          <div className="detail-section">
            <h3>Full Challenge Breakdown</h3>
            {(
              selectedChallenge
                ? [
                    `Duration: ${selectedChallenge.duration ?? '10-20 minutes (adjust as needed)'}`,
                    `Best times (but whenever works): ${selectedChallenge.recommended_times?.join('; ') || 'Whenever works for you'}`,
                    `Suggestions near you: ${selectedChallenge.suggested_locations?.join('; ') || 'Any low-pressure place you feel comfortable'}`,
                    `Interaction required: ${selectedChallenge.interaction_required ?? 'None required - just be present'}`,
                  ]
                : selectedInsights?.full_breakdown?.length
                  ? selectedInsights.full_breakdown
                  : ['Take one manageable social step at your pace.']
            ).map((line, idx) => (
              <p key={`breakdown-${idx}`}>{line}</p>
            ))}
          </div>
          <div className="detail-section">
            <h3>What You&apos;ll Build</h3>
            <p><strong>Skill:</strong> {selectedChallenge?.what_this_builds ?? selectedInsights?.what_youll_build_skill ?? 'Building confidence through repetition.'}</p>
            <p><strong>Prepares you for:</strong> {selectedChallenge?.why_this_works ?? selectedInsights?.what_youll_build_prepares_for ?? 'Steadier social interactions over time.'}</p>
          </div>
          <div className="detail-section">
            <h3>Practical Details</h3>
            <p><strong>Best time:</strong> {selectedChallenge?.recommended_times?.join(' or ') ?? selectedInsights?.practical_best_time ?? 'Choose a quieter hour that feels manageable.'}</p>
            <p><strong>Duration:</strong> {selectedChallenge?.duration ?? selectedInsights?.practical_duration ?? '~20 minutes total.'}</p>
            <p><strong>Near you:</strong> {selectedChallenge?.suggested_locations?.slice(0, 3).join(', ') ?? selectedInsights?.practical_near_you ?? 'Pick a familiar low-pressure place nearby.'}</p>
          </div>
          {selectedChallenge?.suggested_locations && selectedChallenge.suggested_locations.length > 0 && (
            <div className="detail-section">
              <h3>All Suggestions Near You</h3>
              <ul className="suggestion-list">
                {selectedChallenge.suggested_locations.map((loc, idx) => (
                  <li key={`tell-loc-${idx}`}>{loc}</li>
                ))}
              </ul>
            </div>
          )}
          {selectedChallenge?.recommended_times && selectedChallenge.recommended_times.length > 0 && (
            <div className="detail-section">
              <h3>Recommended Times</h3>
              <ul className="suggestion-list">
                {selectedChallenge.recommended_times.map((time, idx) => (
                  <li key={`tell-time-${idx}`}>{time}</li>
                ))}
              </ul>
            </div>
          )}
          {selectedChallenge?.you_can_also && selectedChallenge.you_can_also.length > 0 && (
            <div className="detail-section">
              <h3>You Can Also</h3>
              <ul className="suggestion-list">
                {selectedChallenge.you_can_also.map((option, idx) => (
                  <li key={`tell-alt-${idx}`}>{option}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="detail-section">
            <h3>Exit Strategy</h3>
            <p>{selectedChallenge?.exit_strategy ?? selectedInsights?.exit_strategy ?? 'If it feels awkward, that&apos;s normal. You can leave right after.'}</p>
          </div>
          <div className="detail-section">
            <h3>Modifications</h3>
            <p><strong>Easier:</strong> {selectedChallenge?.modifications?.if_easier_needed ?? selectedInsights?.modification_easier ?? 'Reduce scope and keep it short.'}</p>
            <p><strong>Harder:</strong> {selectedChallenge?.modifications?.if_ready_for_more ?? selectedInsights?.modification_harder ?? 'Add one extra social rep when ready.'}</p>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setShowTellMeMoreModal(false)}>Got It</button>
            <button type="button" className="btn btn-primary" onClick={() => { setShowTellMeMoreModal(false); setShowCompletionModal(true) }}>I&apos;m Ready</button>
          </div>
        </div>
      </div>

      <div className={`modal-overlay ${showPreviewModal ? 'active' : ''}`} onClick={() => setShowPreviewModal(false)}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>Challenge {previewNumber}: Preview</h2>
          <p className="modal-subtitle">🟡 Small Groups</p>
          <div className="detail-section">
            <h3>What This Stage Focuses On</h3>
            <p>This challenge helps you get comfortable being around small groups in structured settings.</p>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-primary full-btn" onClick={() => setShowPreviewModal(false)}>Got It</button>
          </div>
        </div>
      </div>
    </div>
  )
}
