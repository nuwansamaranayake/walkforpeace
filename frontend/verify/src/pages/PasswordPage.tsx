import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { verifyAuth } from '@walkforpeace/shared'

export default function PasswordPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!password.trim()) return
    setLoading(true)
    setError('')
    try {
      await verifyAuth(password)
      navigate('/scan')
    } catch {
      setError('Incorrect password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy flex flex-col items-center justify-center px-4">
      {/* Branding */}
      <div className="mb-8 text-center">
        {/* Lock icon SVG */}
        <div className="flex justify-center mb-4">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#E8930A"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-white tracking-wide">Walk for Peace</h1>
        <p className="text-saffron text-sm mt-1 font-medium uppercase tracking-widest">
          Credential Verification
        </p>
      </div>

      {/* Login card */}
      <div className="w-full max-w-sm bg-navy-light rounded-2xl p-6 shadow-xl border border-white/10">
        <h2 className="text-white text-lg font-semibold mb-5 text-center">Gate Officer Access</h2>

        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="password" className="block text-gray-300 text-sm mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter gate password"
              autoComplete="current-password"
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 text-base border border-gray-600 focus:outline-none focus:border-saffron placeholder-gray-500 transition-colors"
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm mb-4 bg-red-900/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !password.trim()}
            className="w-full bg-saffron hover:bg-saffron-dark disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg py-3 text-base transition-colors"
          >
            {loading ? 'Verifying...' : 'Enter'}
          </button>
        </form>
      </div>

      <p className="text-gray-600 text-xs mt-8 text-center">
        Walk for Peace 2026 &mdash; Authorized Personnel Only
      </p>
    </div>
  )
}
