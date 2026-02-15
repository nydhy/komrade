import type { MoodCheckin } from '../api/checkins'

interface MoodCheckinCardProps {
  checkin: MoodCheckin
}

const MOOD_LABELS: Record<number, string> = {
  1: 'Very low',
  2: 'Low',
  3: 'Okay',
  4: 'Good',
  5: 'Great',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const today = now.toDateString()
  const checkDate = d.toDateString()
  if (today === checkDate) {
    return `Today ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getMoodColorClass(score: number): string {
  if (score <= 2) return 'mood-score-low'
  if (score === 3) return 'mood-score-mid'
  return 'mood-score-high'
}

export function MoodCheckinCard({ checkin }: MoodCheckinCardProps) {
  return (
    <div className="card card-hover mb-3">
      <div className="flex-between mb-3" style={{ flexWrap: 'wrap', gap: '4px' }}>
        <div className="flex-center gap-sm">
          <span className={`mood-score-badge ${getMoodColorClass(checkin.mood_score)}`}>
            {checkin.mood_score}
          </span>
          <span className="heading-sm">
            {MOOD_LABELS[checkin.mood_score] ?? 'Unknown'}
          </span>
        </div>
        <span className="text-muted text-xs">{formatDate(checkin.created_at)}</span>
      </div>

      {checkin.tags.length > 0 && (
        <div className="flex-center gap-xs mb-3" style={{ flexWrap: 'wrap', justifyContent: 'flex-start' }}>
          {checkin.tags.map((t) => (
            <span key={t} className="badge">
              {t}
            </span>
          ))}
        </div>
      )}

      {checkin.note && (
        <p className="text-secondary text-sm mb-2">{checkin.note}</p>
      )}

      {checkin.wants_company && (
        <div className="flex-center gap-xs mt-2" style={{ justifyContent: 'flex-start' }}>
          <span className="badge badge-info">
            Wants company
          </span>
        </div>
      )}
    </div>
  )
}
