import { useEffect, useState } from 'react'
import { getBuddies, type BuddyLinkWithUser } from '../api/buddies'
import { getMe } from '../api/auth'
import { BuddyInviteForm } from '../components/BuddyInviteForm'
import { BuddyList } from '../components/BuddyList'

export default function Buddies() {
  const [links, setLinks] = useState<BuddyLinkWithUser[]>([])
  const [loading, setLoading] = useState(true)
  const [_role, setRole] = useState<string>('')

  async function load() {
    try {
      const token = localStorage.getItem('vetbridge_token')
      if (token) {
        const [me, buddies] = await Promise.all([getMe(token), getBuddies()])
        setRole(me.role)
        setLinks(buddies)
      }
    } catch {
      setLinks([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) {
    return (
      <div className="page-container flex-center" style={{ minHeight: '60vh' }}>
        <div className="card flex-center gap-md animate-in">
          <div className="animate-spin" style={{ width: 24, height: 24, border: '3px solid var(--border-default)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%' }} />
          <span className="text-secondary">Loading buddies…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container page-container-narrow">
      <div className="animate-in mb-8">
        <h1 className="heading-lg mb-2">My Buddies</h1>
        <p className="text-secondary">Manage your connections and friend requests</p>
      </div>

      <div className="animate-in animate-in-delay-1 mb-8">
        <BuddyInviteForm onInvited={load} existingLinks={links} />
      </div>

      <div className="animate-in animate-in-delay-2">
        <h2 className="heading-md mb-4">Buddy Links</h2>
        <BuddyList links={links} onUpdated={load} />
      </div>
    </div>
  )
}
