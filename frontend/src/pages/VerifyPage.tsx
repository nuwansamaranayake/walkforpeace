import { useState, useEffect, useRef } from 'react'
import { Html5QrcodeScanner } from 'html5-qrcode'
import { CheckCircle, XCircle, ScanLine, RotateCcw } from 'lucide-react'
import { verifyCredential } from '../services/api'

export default function VerifyPage() {
  const [result, setResult] = useState<any>(null)
  const [scanning, setScanning] = useState(true)
  const [error, setError] = useState('')
  const scannerRef = useRef<Html5QrcodeScanner | null>(null)

  useEffect(() => {
    if (!scanning) return

    const scanner = new Html5QrcodeScanner('qr-reader', {
      fps: 10,
      qrbox: { width: 250, height: 250 },
      rememberLastUsedCamera: true,
    }, false)

    scanner.render(
      async (decodedText) => {
        scanner.clear()
        setScanning(false)

        // Extract token from URL
        const match = decodedText.match(/\/api\/verify\/(.+)$/)
        const token = match ? match[1] : decodedText

        try {
          const { data } = await verifyCredential(token)
          setResult(data)
        } catch {
          setResult({ valid: false, status: 'invalid', message: 'Could not verify credential.' })
        }
      },
      () => {} // ignore errors during scanning
    )

    scannerRef.current = scanner
    return () => { scanner.clear().catch(() => {}) }
  }, [scanning])

  const reset = () => {
    setResult(null)
    setError('')
    setScanning(true)
  }

  return (
    <div className="min-h-screen bg-navy">
      {/* Header */}
      <div className="text-center py-6">
        <h1 className="text-xl font-bold text-saffron">Walk for Peace</h1>
        <p className="text-gold text-sm">Credential Verification</p>
      </div>

      <div className="max-w-sm mx-auto px-4 pb-8">
        {scanning && !result ? (
          <div>
            <div className="bg-white rounded-2xl overflow-hidden shadow-lg">
              <div className="p-4 text-center">
                <ScanLine className="w-8 h-8 text-saffron mx-auto mb-2" />
                <p className="text-sm text-gray-600">Point camera at QR code</p>
              </div>
              <div id="qr-reader" className="w-full" />
            </div>
          </div>
        ) : result ? (
          <div className="text-center">
            {/* Result card */}
            <div className={`rounded-2xl shadow-lg p-8 ${result.valid ? 'bg-white' : 'bg-white'}`}>
              {result.valid ? (
                <>
                  <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-14 h-14 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-green-600 mb-4">VERIFIED</h2>
                  <hr className="mb-4" />

                  {result.face_photo_url && (
                    <img src={result.face_photo_url} alt="Face"
                      className="w-28 h-28 rounded-full object-cover mx-auto mb-4 border-4 border-green-200" />
                  )}

                  <h3 className="text-xl font-bold text-navy">{result.full_name}</h3>
                  <p className="text-gray-600">{result.organization}</p>
                  <p className="text-gray-500 text-sm mb-3">{result.designation}</p>

                  <div className="inline-block bg-saffron text-white px-4 py-1 rounded-full text-sm font-medium capitalize mb-3">
                    {result.media_type}
                  </div>

                  <div className="bg-green-50 rounded-lg p-3 mt-2">
                    <p className="text-green-700 text-sm font-medium">Badge: {result.badge_number}</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-24 h-24 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <XCircle className="w-14 h-14 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-red-600 mb-2">
                    {result.status === 'expired' ? 'EXPIRED' :
                     result.status === 'revoked' ? 'REVOKED' : 'INVALID'}
                  </h2>
                  <p className="text-gray-600">{result.message}</p>
                </>
              )}
            </div>

            <button onClick={reset}
              className="mt-6 bg-saffron text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto hover:bg-saffron-dark transition">
              <RotateCcw className="w-4 h-4" /> Scan Another
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
