import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { verifyAuth } from '@walkforpeace/shared'

function parseDeviceName(ua: string): string {
  const mobile = ua.match(/\(([^)]+)\)/)
  if (mobile) {
    const parts = mobile[1]
    const android = parts.match(/;\s*(SM-[A-Z0-9]+|Pixel\s*\w+|Redmi\s*[^\s;]+|SAMSUNG\s*[^\s;]+|Xiaomi\s*[^\s;]+|OPPO\s*[^\s;]+|vivo\s*[^\s;]+|OnePlus\s*[^\s;]+|Huawei\s*[^\s;]+)/i)
    if (android) return android[1].trim()
    if (parts.includes('iPhone')) return 'iPhone'
    if (parts.includes('iPad')) return 'iPad'
  }
  if (ua.includes('Windows')) return 'Windows PC'
  if (ua.includes('Mac')) return 'Mac'
  if (ua.includes('Linux')) return 'Linux PC'
  return 'Unknown Device'
}

export default function PasswordPage() {
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!password.trim()) return
    setLoading(true)
    setError('')
    try {
      await verifyAuth(password, {
        device_info: navigator.userAgent,
        device_name: parseDeviceName(navigator.userAgent),
        screen_size: `${screen.width}x${screen.height}`,
      })
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
        <img src="/logo.png" alt="Walk for Peace" className="w-16 h-16 mx-auto mb-3 object-contain" />
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
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter gate password"
                autoComplete="current-password"
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 pr-12 text-base border border-gray-600 focus:outline-none focus:border-saffron placeholder-gray-500 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
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
