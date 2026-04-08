import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Clock, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react'
import { checkStatus } from '@walkforpeace/shared'
import type { StatusResponse } from '@walkforpeace/shared'

const statusConfig: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  pending_review: { icon: Clock, color: 'text-saffron', label: 'Pending Review' },
  approved: { icon: CheckCircle, color: 'text-green-500', label: 'Approved' },
  rejected: { icon: XCircle, color: 'text-red-500', label: 'Rejected' },
  revoked: { icon: XCircle, color: 'text-red-400', label: 'Revoked' },
}

export default function StatusPage() {
  const { refNumber } = useParams()
  const navigate = useNavigate()
  const [inputRef, setInputRef] = useState(refNumber || '')
  const [data, setData] = useState<StatusResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!refNumber) return
    setLoading(true)
    checkStatus(refNumber)
      .then(r => setData(r))
      .catch(() => setError('Application not found. Please check your reference number.'))
      .finally(() => setLoading(false))
  }, [refNumber])

  // No ref param — show search form
  if (!refNumber) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-navy text-white py-6 text-center">
          <Link to="/">
            <h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1>
          </Link>
          <p className="text-gold text-sm mt-1">Check Application Status</p>
        </div>
        <div className="max-w-md mx-auto px-4 py-12">
          <div className="bg-white rounded-xl shadow p-8">
            <p className="text-gray-600 mb-5 text-center text-sm">
              Enter your reference number to check the status of your media credential application.
            </p>
            <form
              onSubmit={e => {
                e.preventDefault()
                const ref = inputRef.trim()
                if (ref) navigate(`/status/${ref}`)
              }}
            >
              <input
                value={inputRef}
                onChange={e => setInputRef(e.target.value)}
                placeholder="e.g. WFP-A1B2C3"
                required
                className="w-full border rounded-lg px-4 py-3 text-center font-mono text-lg mb-4 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
              <button
                type="submit"
                className="w-full bg-saffron text-white py-2.5 rounded-lg font-semibold hover:bg-saffron-dark transition"
              >
                Check Status
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-navy text-white py-6 text-center">
        <Link to="/">
          <h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1>
        </Link>
        <p className="text-gold text-sm mt-1">Application Status</p>
      </div>

      <div className="max-w-md mx-auto px-4 py-12">
        {loading ? (
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-saffron mx-auto" />
            <p className="text-gray-500 mt-3 text-sm">Looking up your application...</p>
          </div>
        ) : error ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <p className="text-gray-600 mb-5">{error}</p>
            <Link
              to="/status"
              className="inline-block bg-saffron text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-saffron-dark transition"
            >
              Try Again
            </Link>
          </div>
        ) : data ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            {(() => {
              const cfg = statusConfig[data.status] || statusConfig.pending_review
              const Icon = cfg.icon
              return <Icon className={`w-16 h-16 ${cfg.color} mx-auto mb-4`} />
            })()}
            <h2 className="text-xl font-bold text-navy mb-1">{data.full_name}</h2>
            <p className="text-gray-500 text-sm mb-5">{data.organization}</p>

            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-xs text-gray-400 mb-1">Reference Number</p>
              <p className="font-mono font-bold text-lg text-navy">{data.ref_number}</p>
            </div>

            <span
              className={`inline-block px-4 py-2 rounded-full font-semibold text-sm ${
                data.status === 'approved'
                  ? 'bg-green-100 text-green-700'
                  : data.status === 'rejected' || data.status === 'revoked'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-orange-100 text-orange-700'
              }`}
            >
              {statusConfig[data.status]?.label || data.status}
            </span>

            {data.status === 'approved' && data.credential && (
              <div className="mt-5">
                <Link
                  to="/get-qr"
                  className="inline-block bg-saffron text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-saffron-dark transition"
                >
                  Retrieve QR Code
                </Link>
              </div>
            )}

            <div className="mt-5">
              <Link to="/status" className="text-xs text-gray-400 hover:text-saffron">
                Check another reference
              </Link>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
