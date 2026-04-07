import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { checkStatus } from '../services/api'

export default function StatusPage() {
  const { refNumber } = useParams()
  const [inputRef, setInputRef] = useState('')
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!refNumber) return
    checkStatus(refNumber)
      .then(r => setData(r.data))
      .catch(() => setError('Application not found'))
      .finally(() => setLoading(false))
  }, [refNumber])

  // If no refNumber in URL, show input form
  if (!refNumber) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-navy text-white py-6 text-center">
          <Link to="/"><h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1></Link>
          <p className="text-gold text-sm">Check Application Status</p>
        </div>
        <div className="max-w-md mx-auto px-4 py-12">
          <div className="bg-white rounded-xl shadow p-8">
            <p className="text-gray-600 mb-4 text-center">Enter your reference number to check your application status.</p>
            <form onSubmit={(e) => { e.preventDefault(); if (inputRef.trim()) navigate(`/status/${inputRef.trim()}`) }}>
              <input value={inputRef} onChange={e => setInputRef(e.target.value)}
                placeholder="e.g. WFP-A1B2C3" required
                className="w-full border rounded-lg px-4 py-3 text-center font-mono text-lg mb-4 focus:ring-2 focus:ring-saffron focus:border-transparent" />
              <button type="submit" className="w-full bg-saffron text-white py-2 rounded-lg font-medium hover:bg-saffron-dark transition">
                Check Status
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  const statusConfig: Record<string, { icon: any; color: string; label: string }> = {
    pending_review: { icon: Clock, color: 'text-saffron', label: 'Pending Review' },
    approved: { icon: CheckCircle, color: 'text-green-500', label: 'Approved' },
    rejected: { icon: XCircle, color: 'text-red-500', label: 'Rejected' },
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-navy text-white py-6 text-center">
        <Link to="/"><h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1></Link>
        <p className="text-gold text-sm">Application Status</p>
      </div>
      <div className="max-w-md mx-auto px-4 py-12">
        {loading ? (
          <div className="text-center"><Loader2 className="w-8 h-8 animate-spin text-saffron mx-auto" /></div>
        ) : error ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <p className="text-gray-600">{error}</p>
          </div>
        ) : data ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            {(() => {
              const cfg = statusConfig[data.status] || statusConfig.pending_review
              const Icon = cfg.icon
              return <Icon className={`w-16 h-16 ${cfg.color} mx-auto mb-4`} />
            })()}
            <h2 className="text-xl font-bold text-navy mb-1">{data.full_name}</h2>
            <p className="text-gray-500 mb-4">{data.organization}</p>
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-500">Reference</p>
              <p className="font-mono font-bold text-lg">{data.ref_number}</p>
            </div>
            <div className={`inline-block px-4 py-2 rounded-full font-semibold text-sm ${
              data.status === 'approved' ? 'bg-green-100 text-green-700' :
              data.status === 'rejected' ? 'bg-red-100 text-red-700' :
              'bg-orange-100 text-orange-700'
            }`}>
              {statusConfig[data.status]?.label || data.status}
            </div>
            <p className="text-xs text-gray-400 mt-4">
              Submitted: {new Date(data.submitted_at).toLocaleDateString()}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
