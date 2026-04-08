import { useEffect, useRef, useState, useCallback } from 'react'
import { Html5Qrcode } from 'html5-qrcode'

interface QRScannerProps {
  onScan: (decodedText: string) => void
  scanning: boolean
}

export default function QRScanner({ onScan, scanning }: QRScannerProps) {
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const mountedRef = useRef(false)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [maxZoom, setMaxZoom] = useState(1)
  const [hasZoom, setHasZoom] = useState(false)
  const trackRef = useRef<MediaStreamTrack | null>(null)

  const applyZoom = useCallback(async (value: number) => {
    const track = trackRef.current
    if (!track) return
    try {
      await (track as any).applyConstraints({ advanced: [{ zoom: value }] })
      setZoom(value)
    } catch {
      // zoom not supported
    }
  }, [])

  useEffect(() => {
    if (!scanning) {
      if (scannerRef.current?.isScanning) {
        scannerRef.current.stop().catch(() => {})
      }
      trackRef.current = null
      mountedRef.current = false
      return
    }

    if (mountedRef.current) return
    mountedRef.current = true

    const scanner = new Html5Qrcode('qr-reader')
    scannerRef.current = scanner
    setStarting(true)
    setError('')

    scanner
      .start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 }, aspectRatio: 1.0 },
        (decodedText) => onScan(decodedText),
        () => {},
      )
      .then(() => {
        setStarting(false)
        // Check for zoom capability
        try {
          const videoElem = document.querySelector('#qr-reader video') as HTMLVideoElement
          if (videoElem?.srcObject) {
            const stream = videoElem.srcObject as MediaStream
            const track = stream.getVideoTracks()[0]
            trackRef.current = track
            const caps = track.getCapabilities() as any
            if (caps?.zoom) {
              setHasZoom(true)
              setMaxZoom(caps.zoom.max || 5)
              setZoom(caps.zoom.min || 1)
            }
          }
        } catch {
          // zoom detection failed, no-op
        }
      })
      .catch((err: Error) => {
        setStarting(false)
        if (err.message?.includes('Permission')) {
          setError('Camera permission denied. Please allow camera access in your browser settings and reload.')
        } else {
          setError('Could not start camera. Make sure no other app is using it, then reload.')
        }
      })

    return () => {
      if (scannerRef.current?.isScanning) {
        scannerRef.current.stop().catch(() => {})
      }
      trackRef.current = null
      mountedRef.current = false
    }
  }, [scanning, onScan])

  if (!scanning) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M3 7V5a2 2 0 0 1 2-2h2" />
          <path d="M17 3h2a2 2 0 0 1 2 2v2" />
          <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
          <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
          <rect x="7" y="7" width="10" height="10" />
        </svg>
        <p className="mt-3 text-sm">Camera paused</p>
      </div>
    )
  }

  return (
    <div className="w-full relative">
      <div id="qr-reader" className="w-full" />
      {starting && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80">
          <svg className="animate-spin" width="36" height="36" viewBox="0 0 24 24" fill="none"
            stroke="#E8930A" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
            <path d="M12 2a10 10 0 0 1 10 10" />
          </svg>
          <p className="mt-3 text-gray-300 text-sm">Starting camera...</p>
        </div>
      )}
      {error && (
        <div className="p-4 text-center">
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-saffron hover:bg-saffron-dark text-white text-sm font-semibold rounded-lg px-4 py-2 transition-colors"
          >
            Reload
          </button>
        </div>
      )}
      {/* Zoom slider */}
      {hasZoom && !starting && !error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-navy/90 rounded-b-xl">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
          <input
            type="range"
            min="1"
            max={maxZoom}
            step="0.1"
            value={zoom}
            onChange={(e) => applyZoom(parseFloat(e.target.value))}
            className="flex-1 h-1.5 bg-gray-600 rounded-full appearance-none cursor-pointer accent-saffron"
          />
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E8930A"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
          <span className="text-gray-400 text-xs font-mono w-8 text-right">{zoom.toFixed(1)}x</span>
        </div>
      )}
    </div>
  )
}
