import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { verifyCredential } from '@walkforpeace/shared'
import type { VerifyResponse } from '@walkforpeace/shared'
import QRScanner from '../components/QRScanner'
import ResultApproved from '../components/ResultApproved'
import ResultFlagged from '../components/ResultFlagged'
import ResultRejected from '../components/ResultRejected'

type PageState = 'scanning' | 'loading' | 'result'

function extractToken(decodedText: string): string {
  // Try to extract from URL: /api/verify/<token>
  const urlMatch = decodedText.match(/\/api\/verify\/(.+)$/)
  if (urlMatch) return urlMatch[1].trim()
  // Also try path-only pattern: /verify/<token>
  const pathMatch = decodedText.match(/\/verify\/(.+)$/)
  if (pathMatch) return pathMatch[1].trim()
  // Otherwise treat the whole string as the token
  return decodedText.trim()
}

export default function ScanPage() {
  const navigate = useNavigate()
  const [pageState, setPageState] = useState<PageState>('scanning')
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [currentToken, setCurrentToken] = useState('')
  const [scanError, setScanError] = useState('')
  // Prevent duplicate scans of same QR within a session
  const [lastScanned, setLastScanned] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('verify_session')) {
      navigate('/', { replace: true })
    }
  }, [navigate])

  const handleScan = useCallback(async (decodedText: string) => {
    if (pageState !== 'scanning') return
    if (decodedText === lastScanned) return

    setLastScanned(decodedText)
    const token = extractToken(decodedText)
    setCurrentToken(token)
    setPageState('loading')
    setScanError('')

    try {
      const data = await verifyCredential(token)
      setResult(data)
      setPageState('result')
    } catch {
      setScanError('Could not verify credential. Check connection and try again.')
      setPageState('scanning')
      setLastScanned('')
    }
  }, [pageState, lastScanned])

  const handleScanNext = useCallback(() => {
    setResult(null)
    setCurrentToken('')
    setScanError('')
    setLastScanned('')
    setPageState('scanning')
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('verify_session')
    navigate('/', { replace: true })
  }

  const verificationStatus = result?.verification_status ?? result?.status ?? ''

  return (
    <div className="min-h-screen bg-navy flex flex-col">
      {/* Header */}
      <header className="bg-navy-light border-b border-white/10 px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-saffron font-bold text-sm tracking-widest uppercase">Walk for Peace</p>
          <p className="text-gray-400 text-xs">Gate Verification</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-gray-400 hover:text-white text-xs border border-gray-600 hover:border-gray-400 rounded px-3 py-1.5 transition-colors"
        >
          Logout
        </button>
      </header>

      <main className="flex-1 flex flex-col px-4 py-5 gap-5 max-w-lg mx-auto w-full">
        {/* Scanner area */}
        {pageState !== 'result' && (
          <div className="bg-navy-light rounded-xl border border-white/10 overflow-hidden">
            <div className="px-4 pt-4 pb-2 flex items-center gap-2">
              {/* Scan icon */}
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#E8930A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 7V5a2 2 0 0 1 2-2h2" />
                <path d="M17 3h2a2 2 0 0 1 2 2v2" />
                <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
                <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
                <rect x="7" y="7" width="10" height="10" />
              </svg>
              <span className="text-white text-sm font-semibold">
                {pageState === 'loading' ? 'Verifying...' : 'Point camera at badge QR code'}
              </span>
            </div>

            {pageState === 'loading' ? (
              <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                <svg
                  className="animate-spin"
                  width="36"
                  height="36"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#E8930A"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" />
                </svg>
                <p className="mt-3 text-sm">Checking credential...</p>
              </div>
            ) : (
              <QRScanner onScan={handleScan} scanning={pageState === 'scanning'} />
            )}
          </div>
        )}

        {/* Error message */}
        {scanError && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-3">
            <p className="text-red-300 text-sm">{scanError}</p>
          </div>
        )}

        {/* Result card */}
        {pageState === 'result' && result && (
          <>
            {verificationStatus === 'approved' && (
              <ResultApproved result={result} onScanNext={handleScanNext} />
            )}
            {verificationStatus === 'flagged' && (
              <ResultFlagged result={result} token={currentToken} onScanNext={handleScanNext} />
            )}
            {verificationStatus !== 'approved' && verificationStatus !== 'flagged' && (
              <ResultRejected result={result} onScanNext={handleScanNext} />
            )}
          </>
        )}
      </main>
    </div>
  )
}
