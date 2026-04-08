import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, QrCode, Download, AlertCircle } from 'lucide-react'
import { retrieveByPIN, retrieveByIDNumber, StatusBadge } from '@walkforpeace/shared'
import type { RetrieveResponse } from '@walkforpeace/shared'

type Tab = 'pin' | 'id'

export default function GetQRPage() {
  const [tab, setTab] = useState<Tab>('pin')
  const [pinInput, setPinInput] = useState('')
  const [idInput, setIdInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<RetrieveResponse | null>(null)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)

    try {
      let data: RetrieveResponse
      if (tab === 'pin') {
        data = await retrieveByPIN(pinInput.trim().toUpperCase())
      } else {
        data = await retrieveByIDNumber(idInput.trim())
      }
      setResult(data)
    } catch (err: any) {
      const msg = err.response?.data?.detail
      setError(msg || 'No record found. Please check your details and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-navy text-white py-6">
        <div className="max-w-lg mx-auto px-4 text-center">
          <Link to="/" className="inline-block">
            <h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1>
          </Link>
          <p className="text-gold text-sm mt-1">Retrieve Your QR Code</p>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-10">
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-gray-100">
            <button
              type="button"
              onClick={() => { setTab('pin'); setError(''); setResult(null) }}
              className={`flex-1 py-3 text-sm font-semibold transition ${
                tab === 'pin'
                  ? 'text-saffron border-b-2 border-saffron bg-saffron/5'
                  : 'text-gray-500 hover:text-navy'
              }`}
            >
              By PIN
            </button>
            <button
              type="button"
              onClick={() => { setTab('id'); setError(''); setResult(null) }}
              className={`flex-1 py-3 text-sm font-semibold transition ${
                tab === 'id'
                  ? 'text-saffron border-b-2 border-saffron bg-saffron/5'
                  : 'text-gray-500 hover:text-navy'
              }`}
            >
              By NIC / Passport
            </button>
          </div>

          <div className="p-6">
            <form onSubmit={handleSearch}>
              {tab === 'pin' ? (
                <div className="mb-5">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Your PIN Code
                  </label>
                  <input
                    value={pinInput}
                    onChange={e => setPinInput(e.target.value)}
                    placeholder="WFP-XXXXXX"
                    required
                    className="w-full border rounded-lg px-4 py-3 font-mono text-lg text-center focus:ring-2 focus:ring-saffron focus:border-transparent uppercase tracking-widest"
                  />
                  <p className="text-xs text-gray-400 mt-1 text-center">
                    Your PIN was shown after registration. Format: WFP-XXXXXX
                  </p>
                </div>
              ) : (
                <div className="mb-5">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NIC or Passport Number
                  </label>
                  <input
                    value={idInput}
                    onChange={e => setIdInput(e.target.value)}
                    placeholder="e.g. 199012345678 or N1234567"
                    required
                    className="w-full border rounded-lg px-4 py-3 font-mono text-center focus:ring-2 focus:ring-saffron focus:border-transparent"
                  />
                  <p className="text-xs text-gray-400 mt-1 text-center">
                    Enter the same ID number you used during registration.
                  </p>
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 flex items-start gap-2 text-sm">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-saffron text-white py-2.5 rounded-lg font-semibold hover:bg-saffron-dark transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Looking up...
                  </>
                ) : (
                  <>
                    <QrCode className="w-4 h-4" /> Retrieve QR Code
                  </>
                )}
              </button>
            </form>

            {/* Result */}
            {result && (
              <div className="mt-6 border-t border-gray-100 pt-6">
                <div className="text-center mb-4">
                  <p className="text-sm text-gray-500">Application for</p>
                  <h3 className="text-lg font-bold text-navy">{result.full_name}</h3>
                  <p className="text-sm text-gray-600">{result.organization}</p>
                  <div className="mt-2 flex items-center justify-center gap-3">
                    <span className="text-xs font-mono text-gray-400">{result.ref_number}</span>
                    <StatusBadge status={result.verification_status} />
                  </div>
                </div>

                {result.qr_code_url ? (
                  <div className="text-center">
                    <img
                      src={result.qr_code_url}
                      alt="QR Code"
                      className="w-48 h-48 mx-auto border-2 border-gray-200 rounded-xl object-contain"
                    />
                    <p className="text-xs text-gray-400 mt-2 mb-4">
                      Show this QR code at the event entrance.
                    </p>
                    {result.badge_pdf_url && (
                      <a
                        href={result.badge_pdf_url}
                        download
                        className="inline-flex items-center gap-2 bg-navy text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-navy-light transition"
                      >
                        <Download className="w-4 h-4" /> Download Badge PDF
                      </a>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-4 text-sm text-gray-500">
                    {result.status === 'pending_review'
                      ? 'Your application is pending review. QR code will be available once approved.'
                      : result.status === 'rejected'
                      ? 'Your application was not approved.'
                      : 'QR code not yet generated.'}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <p className="text-center text-sm text-gray-400 mt-6">
          Not yet registered?{' '}
          <Link to="/register" className="text-saffron hover:underline">
            Apply for a media credential
          </Link>
        </p>
      </div>
    </div>
  )
}
