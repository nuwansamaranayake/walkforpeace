import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { verifyCredential, verifyLogout } from '@walkforpeace/shared'
import type { VerifyResponse } from '@walkforpeace/shared'
import QRScanner from '../components/QRScanner'
import ResultApproved from '../components/ResultApproved'
import ResultFlagged from '../components/ResultFlagged'
import ResultRejected from '../components/ResultRejected'

type PageState = 'scanning' | 'loading' | 'result'

const TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes
const WARNING_MS = 4 * 60 * 1000 // 4 minutes — show warning at this point

function extractToken(decodedText: string): string {
  const urlMatch = decodedText.match(/\/api\/verify\/(.+)$/)
  if (urlMatch) return urlMatch[1].trim()
  const pathMatch = decodedText.match(/\/verify\/(.+)$/)
  if (pathMatch) return pathMatch[1].trim()
  return decodedText.trim()
}

// ─── GPS + Reverse Geocoding ────────────────────────────────────────
let cachedGps: { lat: number; lng: number; place?: string } | null = null
let watchId: number | null = null

function reverseGeocode(lat: number, lng: number) {
  // Nominatim free reverse geocoding — no API key needed
  fetch(
    `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=16`,
    { headers: { 'User-Agent': 'WalkForPeace/1.0' } }
  )
    .then(r => r.json())
    .then(data => {
      if (data?.display_name && cachedGps) {
        // Shorten: "Kandy-Colombo Road, Kandy, Central Province, Sri Lanka" → first 2-3 parts
        const parts = data.display_name.split(', ')
        cachedGps.place = parts.slice(0, 3).join(', ')
      }
    })
    .catch(() => { /* Geocoding failed — that's OK */ })
}

function startGpsTracking() {
  if (!('geolocation' in navigator)) return
  // Get initial position
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      cachedGps = { lat: pos.coords.latitude, lng: pos.coords.longitude }
      reverseGeocode(pos.coords.latitude, pos.coords.longitude)
    },
    () => { /* GPS denied */ },
    { enableHighAccuracy: true, timeout: 10000 }
  )
  // Watch for updates
  if (watchId === null) {
    watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const newLat = pos.coords.latitude
        const newLng = pos.coords.longitude
        // Only re-geocode if moved significantly (~100m)
        const moved = cachedGps
          ? Math.abs(newLat - cachedGps.lat) > 0.001 || Math.abs(newLng - cachedGps.lng) > 0.001
          : true
        cachedGps = { lat: newLat, lng: newLng, place: cachedGps?.place }
        if (moved) reverseGeocode(newLat, newLng)
      },
      () => {},
      { enableHighAccuracy: false, timeout: 30000 }
    )
  }
}

// ─── Device ID ──────────────────────────────────────────────────────
function getDeviceId(): string {
  let id = sessionStorage.getItem('wfp_device_id')
  if (!id) {
    id = crypto.randomUUID?.() || Math.random().toString(36).slice(2)
    sessionStorage.setItem('wfp_device_id', id)
  }
  return id
}

// ─── Component ──────────────────────────────────────────────────────
export default function ScanPage() {
  const navigate = useNavigate()
  const [pageState, setPageState] = useState<PageState>('scanning')
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [currentToken, setCurrentToken] = useState('')
  const [scanError, setScanError] = useState('')
  const [lastScanned, setLastScanned] = useState('')
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false)
  const lastActivityRef = useRef(Date.now())

  // Start GPS tracking on mount (permission was already requested on PasswordPage)
  useEffect(() => { startGpsTracking() }, [])

  // Session check
  useEffect(() => {
    if (!localStorage.getItem('verify_session')) {
      navigate('/', { replace: true })
    }
  }, [navigate])

  // Inactivity auto-logout
  useEffect(() => {
    const resetActivity = () => {
      lastActivityRef.current = Date.now()
      setShowTimeoutWarning(false)
    }

    const events = ['touchstart', 'click', 'scroll', 'keydown']
    events.forEach(e => document.addEventListener(e, resetActivity))

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current
      if (elapsed > TIMEOUT_MS) {
        verifyLogout()
        navigate('/', { replace: true })
      } else if (elapsed > WARNING_MS) {
        setShowTimeoutWarning(true)
      }
    }, 15000)

    return () => {
      events.forEach(e => document.removeEventListener(e, resetActivity))
      clearInterval(interval)
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
      const gpsParams: Record<string, any> = { device_id: getDeviceId() }
      if (cachedGps) {
        gpsParams.lat = cachedGps.lat
        gpsParams.lng = cachedGps.lng
        if (cachedGps.place) gpsParams.place = cachedGps.place
      }
      const data = await verifyCredential(token, gpsParams)
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

  const handleLogout = async () => {
    await verifyLogout()
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

      {/* Timeout warning toast */}
      {showTimeoutWarning && (
        <div className="bg-amber-600 text-white text-center text-sm py-2 px-4">
          Session expires in 1 minute — tap anywhere to stay active
        </div>
      )}

      <main className="flex-1 flex flex-col px-4 py-5 gap-5 max-w-lg mx-auto w-full">
        {/* Scanner area */}
        {pageState !== 'result' && (
          <div className="bg-navy-light rounded-xl border border-white/10 overflow-hidden">
            <div className="px-4 pt-4 pb-2 flex items-center gap-2">
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
