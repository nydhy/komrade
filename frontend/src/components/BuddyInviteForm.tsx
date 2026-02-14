import { useState } from 'react'
import { inviteBuddy, type BuddyLinkWithUser } from '../api/buddies'

interface BuddyInviteFormProps {
  onInvited: () => void
  existingLinks?: BuddyLinkWithUser[]
}

export function BuddyInviteForm({ onInvited, existingLinks = [] }: BuddyInviteFormProps) {
  const [email, setEmail] = useState('')
  const [trustLevel, setTrustLevel] = useState(3)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  function checkAlreadyConnected(emailToCheck: string): string | null {
    const lower = emailToCheck.toLowerCase().trim()
    const existing = existingLinks.find((l) => l.other_email.toLowerCase() === lower)
    if (!existing) return null
    if (existing.status === 'ACCEPTED') return 'You are already friends with this user.'
    if (existing.status === 'PENDING') return 'A friend request is already pending with this user.'
    if (existing.status === 'BLOCKED') return 'This connection has been blocked.'
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')

    const clientCheck = checkAlreadyConnected(email)
    if (clientCheck) {
      setError(clientCheck)
      return
    }

    setLoading(true)
    try {
      await inviteBuddy({ buddy_email: email, trust_level: trustLevel })
      setSuccess(`Friend request sent to ${email}!`)
      setEmail('')
      onInvited()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invite failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card card-glow">
      <h3 className="heading-sm mb-4">Add a Friend</h3>

      <form onSubmit={handleSubmit} className="flex-col gap-md">
        <div className="form-row">
          <div className="input-group">
            <label>Email address</label>
            <input
              type="email"
              className="input"
              placeholder="Enter friend's email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(''); setSuccess('') }}
              required
            />
          </div>

          <div className="input-group">
            <label>Trust level</label>
            <select
              className="select"
              value={trustLevel}
              onChange={(e) => setTrustLevel(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  Trust {n}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Sending…' : 'Send Request'}
          </button>
        </div>

        {error && (
          <div className="alert alert-danger animate-in">
            {error}
          </div>
        )}

        {success && (
          <div className="alert alert-success animate-in">
            {success}
          </div>
        )}
      </form>
    </div>
  )
}
