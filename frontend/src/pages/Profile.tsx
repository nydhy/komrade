import { useEffect, useState } from 'react'
import { getMe, updateProfile, type UserMe } from '../api/auth'
import { getToken } from '../state/authStore'

export default function Profile() {
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [fullName, setFullName] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const token = getToken()
        if (!token) return
        const me = await getMe(token)
        setUser(me)
        setFullName(me.full_name)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await updateProfile({
        full_name: fullName || undefined,
      })
      setUser(updated)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="page-container flex-center" style={{ minHeight: '40vh' }}>
        <p className="text-secondary">Loading profile...</p>
      </div>
    )
  }

  return (
    <div className="page-container page-container-narrow">
      <div className="animate-in mb-8">
        <h1 className="heading-lg mb-2">My Profile</h1>
        <p className="text-muted">Update your personal information</p>
      </div>

      {error && (
        <div className="alert alert-danger animate-in mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success animate-in mb-4">
          Profile saved successfully.
        </div>
      )}

      <form onSubmit={handleSave} className="flex-col gap-lg">
        {/* Account info (read-only) */}
        <section className="card animate-in animate-in-delay-1">
          <h2 className="heading-md mb-4">Account</h2>
          <div className="divider mb-4" />
          <div className="profile-info-grid">
            <span className="text-secondary text-sm">Email</span>
            <span className="text-sm">{user?.email}</span>
            <span className="text-secondary text-sm">Role</span>
            <span className="text-sm" style={{ textTransform: 'capitalize' }}>{user?.role}</span>
            <span className="text-secondary text-sm">Joined</span>
            <span className="text-sm">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : ''}</span>
          </div>
        </section>

        {/* Editable name */}
        <section className="card animate-in animate-in-delay-2">
          <h2 className="heading-md mb-4">Personal Info</h2>
          <div className="divider mb-4" />
          <div className="input-group">
            <label>Full Name</label>
            <input
              type="text"
              className="input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your full name"
            />
          </div>
        </section>

        {/* Save button */}
        <div className="animate-in animate-in-delay-3">
          <button
            type="submit"
            className="btn btn-primary btn-lg w-full"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  )
}
