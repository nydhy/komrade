import { useEffect, useState } from 'react'
import { getMyCheckins, type MoodCheckin } from '../api/checkins'
import { getMe, type UserMe } from '../api/auth'
import { getBuddies, type BuddyLinkWithUser } from '../api/buddies'
import { MoodCheckinCard } from '../components/MoodCheckinCard'
import { MoodCheckinForm } from '../components/MoodCheckinForm'
import { PresenceControl } from '../components/PresenceControl'
import { LocationUpdate } from '../components/LocationUpdate'
import { NearbyBuddiesList } from '../components/NearbyBuddiesList'
import { getToken } from '../state/authStore'

export default function Dashboard() {
  const [checkins, setCheckins] = useState<MoodCheckin[]>([])
  const [buddyLinks, setBuddyLinks] = useState<BuddyLinkWithUser[]>([])
  const [loading, setLoading] = useState(true)
  const [role, setRole] = useState<string>('')
  const [userName, setUserName] = useState<string>('')
  const [loadError, setLoadError] = useState<string | null>(null)

  async function load() {
    setLoadError(null)
    try {
      const token = getToken()
      if (!token) {
        setLoadError('No token found. Please log in again.')
        setLoading(false)
        return
      }
      const me = await getMe(token)
      setRole(me.role)
      setUserName(me.full_name)
      const [checkinData, links] = await Promise.all([getMyCheckins(7), getBuddies()])
      setCheckins(checkinData)
      setBuddyLinks(links)
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : 'Failed to load dashboard. Your session may have expired — please log in again.'
      )
      setCheckins([])
      setBuddyLinks([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const buddyOptions = buddyLinks
    .filter((l) => l.status === 'ACCEPTED')
    .map((l) => ({
      id: l.buddy_id,
      name: l.other_name || l.other_email,
      email: l.other_email,
    }))

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="page-container animate-in">
        <div className="mb-8">
          <div className="loading-shimmer skeleton-heading mb-4" />
          <div className="loading-shimmer skeleton-text" />
        </div>
        <div className="grid-3 mb-8">
          <div className="card loading-shimmer skeleton-card" />
          <div className="card loading-shimmer skeleton-card" />
          <div className="card loading-shimmer skeleton-card" />
        </div>
        <div className="card loading-shimmer skeleton-card mb-6" />
        <div className="card loading-shimmer skeleton-card" />
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* ── Welcome Banner ── */}
      <div className="page-header animate-in">
        <h1 className="heading-xl">
          Welcome{userName ? ', ' : ''}
          {userName && <span className="text-gradient">{userName}</span>}
        </h1>
        <p className="text-secondary text-lg mt-2">
          VetBridge — Veteran Buddy Matching
        </p>
      </div>

      {/* ── Error Alert ── */}
      {loadError && (
        <div className="alert alert-danger animate-in mb-6">
          <div>
            <p className="mb-2">{loadError}</p>
            <a href="/login" className="btn btn-ghost btn-sm">Go to Login</a>
          </div>
        </div>
      )}

      {/* ── Status & Location ── */}
      {role && (
        <section className="card mb-6 animate-in animate-in-delay-1">
          <h2 className="heading-md mb-4">Status &amp; Location</h2>
          <div className="flex-col gap-md">
            <PresenceControl />
            <LocationUpdate />
          </div>
        </section>
      )}

      {role === 'veteran' && (
        <>
          {/* ── Nearby Buddies ── */}
          <section className="card mb-6 animate-in animate-in-delay-2">
            <h2 className="heading-md mb-2">Nearby Buddies</h2>
            <p className="text-secondary text-sm mb-4">
              These are the buddies who will be notified during SOS
            </p>
            <NearbyBuddiesList />
          </section>

          {/* ── Mood Check-in ── */}
          <section className="card mb-6 animate-in animate-in-delay-3">
            <h2 className="heading-md mb-4">Mood Check-in</h2>
            <MoodCheckinForm
              onSubmitted={load}
              buddies={buddyOptions}
            />

            <hr className="divider" />

            <h3 className="heading-sm mb-3">Recent check-ins (last 7)</h3>
            {checkins.length === 0 ? (
              <p className="text-muted text-sm">No check-ins yet. Submit your first one above.</p>
            ) : (
              <div className="flex-col gap-sm">
                {checkins.map((c) => (
                  <MoodCheckinCard key={c.id} checkin={c} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {role !== 'veteran' && role && (
        <div className="card animate-in animate-in-delay-1">
          <p className="text-secondary">Mood check-ins and SOS are available for veterans.</p>
        </div>
      )}
    </div>
  )
}
