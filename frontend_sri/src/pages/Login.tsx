import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { login, type LoginRequest } from '../api/auth'
import { setToken } from '../state/authStore'
import { updatePresence } from '../api/presence'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data: LoginRequest = { email, password }
      const res = await login(data)
      setToken(res.access_token)
      try { await updatePresence('AVAILABLE') } catch { /* ignore */ }
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ambient-bg flex-center" style={{ minHeight: '100vh' }}>
      <div className="card glow-border animate-in" style={{ width: '100%', maxWidth: 440 }}>
        {/* ── Logo / Header ── */}
        <div className="text-center mb-8">
          <h1 className="heading-xl text-gradient mb-2">VetBridge</h1>
          <p className="text-secondary">Welcome back to the veteran support network</p>
        </div>

        <hr className="divider" />

        {/* ── Form ── */}
        <h2 className="heading-md text-center mb-6">Sign in to your account</h2>

        <form onSubmit={handleSubmit}>
          <div className="input-group mb-4">
            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="john@example.com"
              required
              autoComplete="email"
              className="input"
            />
          </div>

          <div className="input-group mb-6">
            <label htmlFor="login-password">Password</label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
                className="input"
                style={{ paddingRight: '4rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="btn btn-ghost btn-sm absolute"
                style={{ right: 4, top: '50%', transform: 'translateY(-50%)' }}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          {error && (
            <div className="alert alert-danger mb-4 animate-in">
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-lg w-full"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {/* ── Footer ── */}
        <div className="text-center mt-6">
          <hr className="divider" />
          <p className="text-secondary text-sm">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-gradient" style={{ fontWeight: 600 }}>
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
