import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Loader2, AlertCircle } from 'lucide-react'
import { adminLogin, changePassword } from '@walkforpeace/shared'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mustChange, setMustChange] = useState(false)
  const [newPwd, setNewPwd] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await adminLogin(username, password)
      if (data.must_change_password) {
        setMustChange(true)
      } else {
        navigate('/dashboard')
      }
    } catch {
      setError('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await changePassword(password, newPwd)
      navigate('/dashboard')
    } catch {
      setError('Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-sm w-full">
        <div className="text-center mb-6">
          <Shield className="w-12 h-12 text-saffron mx-auto mb-3" />
          <h1 className="text-xl font-bold text-navy">Admin Dashboard</h1>
          <p className="text-gray-500 text-sm">Walk for Peace Sri Lanka</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 rounded-lg p-3 mb-4 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {mustChange ? (
          <form onSubmit={handleChangePassword}>
            <p className="text-sm text-gray-600 mb-4">You must change your password before continuing.</p>
            <input
              type="password"
              placeholder="New password (min 8 chars)"
              value={newPwd}
              onChange={e => setNewPwd(e.target.value)}
              required
              minLength={8}
              className="w-full border rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-saffron"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-saffron text-white py-2 rounded-lg font-medium disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Set New Password'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="w-full border rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-saffron"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full border rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-saffron"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-saffron text-white py-2 rounded-lg font-medium disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Sign In'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
