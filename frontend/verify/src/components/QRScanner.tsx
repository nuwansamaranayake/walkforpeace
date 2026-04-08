import { useEffect, useRef } from 'react'
import { Html5QrcodeScanner, Html5QrcodeScanType } from 'html5-qrcode'

interface QRScannerProps {
  onScan: (decodedText: string) => void
  scanning: boolean
}

export default function QRScanner({ onScan, scanning }: QRScannerProps) {
  const scannerRef = useRef<Html5QrcodeScanner | null>(null)
  const mountedRef = useRef(false)

  useEffect(() => {
    if (!scanning) {
      // Clean up scanner if it exists
      if (scannerRef.current) {
        scannerRef.current.clear().catch(() => {})
        scannerRef.current = null
      }
      mountedRef.current = false
      return
    }

    // Avoid double-init in StrictMode
    if (mountedRef.current) return
    mountedRef.current = true

    const scanner = new Html5QrcodeScanner(
      'qr-reader',
      {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
        aspectRatio: 1.0,
      },
      /* verbose= */ false,
    )

    scanner.render(
      (decodedText) => {
        onScan(decodedText)
      },
      (errorMessage) => {
        // Suppress per-frame errors — they are expected when no QR in view
        void errorMessage
      },
    )

    scannerRef.current = scanner

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(() => {})
        scannerRef.current = null
      }
      mountedRef.current = false
    }
  }, [scanning, onScan])

  if (!scanning) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        {/* Scan icon SVG */}
        <svg
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
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
        <p className="mt-3 text-sm">Camera paused</p>
      </div>
    )
  }

  return <div id="qr-reader" className="w-full" />
}
