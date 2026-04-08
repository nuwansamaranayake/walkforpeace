import { useLocation, Link, Navigate } from 'react-router-dom'
import { useState } from 'react'
import { CheckCircle, Copy, Check, QrCode, AlertTriangle } from 'lucide-react'

interface ConfirmState {
  pin_code: string
  ref_number: string
  qr_code_url: string
}

export default function ConfirmationPage() {
  const location = useLocation()
  const state = location.state as ConfirmState | null
  const [copied, setCopied] = useState(false)

  // Guard: if navigated directly without state, redirect home
  if (!state?.pin_code || !state?.ref_number) {
    return <Navigate to="/" replace />
  }

  const { pin_code, ref_number, qr_code_url } = state

  const copyPin = async () => {
    try {
      await navigator.clipboard.writeText(pin_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard not available
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-navy text-white py-6">
        <div className="max-w-lg mx-auto px-4 text-center">
          <h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1>
          <p className="text-gold text-sm mt-1">Media Credential Registration</p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="bg-white rounded-2xl shadow-lg max-w-md w-full overflow-hidden">
          {/* Success banner */}
          <div className="bg-green-50 border-b border-green-100 px-6 py-5 text-center">
            <CheckCircle className="w-14 h-14 text-green-500 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-green-800">Application Submitted!</h2>
            <p className="text-green-700 text-sm mt-1">
              Your media credential application has been received.
            </p>
          </div>

          <div className="px-6 py-6 space-y-5">
            {/* PIN — prominent */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 text-center">
                Your PIN Code
              </p>
              <div className="bg-saffron/10 border-2 border-saffron rounded-xl px-6 py-5 text-center">
                <span className="text-3xl font-mono font-bold text-saffron tracking-widest">
                  {pin_code}
                </span>
                <button
                  type="button"
                  onClick={copyPin}
                  className="ml-3 inline-flex items-center gap-1 text-saffron hover:text-saffron-dark transition text-sm"
                  title="Copy PIN"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* Save PIN warning */}
            <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800 font-medium">
                Save your PIN — you'll need it to retrieve your QR code later.
              </p>
            </div>

            {/* Reference number */}
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-1">Reference Number</p>
              <p className="font-mono font-semibold text-navy text-lg">{ref_number}</p>
            </div>

            {/* QR code if available */}
            {qr_code_url && (
              <div className="text-center">
                <p className="text-xs text-gray-400 mb-2 flex items-center justify-center gap-1">
                  <QrCode className="w-3.5 h-3.5" /> Your QR Code (pending approval)
                </p>
                <img
                  src={qr_code_url}
                  alt="QR Code"
                  className="w-40 h-40 mx-auto border-2 border-gray-200 rounded-xl object-contain"
                />
              </div>
            )}

            {/* Next steps */}
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600 space-y-1">
              <p className="font-medium text-gray-800 mb-2">Next steps:</p>
              <p>1. Your application will be reviewed by our team.</p>
              <p>2. You'll receive an email once a decision is made.</p>
              <p>3. Once approved, retrieve your QR code using your PIN.</p>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-3 pt-2">
              <Link
                to="/get-qr"
                className="w-full text-center bg-saffron text-white py-2.5 rounded-lg font-semibold hover:bg-saffron-dark transition text-sm"
              >
                Retrieve QR Code with PIN
              </Link>
              <Link
                to={`/status/${ref_number}`}
                className="w-full text-center border border-navy text-navy py-2.5 rounded-lg font-semibold hover:bg-navy hover:text-white transition text-sm"
              >
                Check Application Status
              </Link>
              <Link
                to="/"
                className="w-full text-center text-gray-400 hover:text-gray-600 py-2 text-sm transition"
              >
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
