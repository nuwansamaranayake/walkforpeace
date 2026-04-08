import { useState, useRef, useCallback } from 'react'
import type { VerifyResponse } from '@walkforpeace/shared'
import { gateApprove, gateDeny } from '@walkforpeace/shared'

interface ResultFlaggedProps {
  result: VerifyResponse
  token: string
  onScanNext: () => void
}

export default function ResultFlagged({ result, token, onScanNext }: ResultFlaggedProps) {
  const [holdProgress, setHoldProgress] = useState(0)
  const [actionDone, setActionDone] = useState<'approved' | 'denied' | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState('')

  const holdTimer = useRef<number | undefined>(undefined)
  const startTime = useRef<number | undefined>(undefined)

  const handleApprove = useCallback(async () => {
    if (actionLoading) return
    setActionLoading(true)
    setActionError('')
    try {
      await gateApprove(token)
      setActionDone('approved')
    } catch {
      setActionError('Gate approve failed. Try again.')
      setHoldProgress(0)
    } finally {
      setActionLoading(false)
    }
  }, [token, actionLoading])

  const onPointerDown = useCallback(() => {
    if (actionDone || actionLoading) return
    startTime.current = Date.now()

    const animate = () => {
      const elapsed = Date.now() - (startTime.current ?? Date.now())
      const progress = Math.min(elapsed / 2000, 1)
      setHoldProgress(progress)
      if (progress < 1) {
        holdTimer.current = requestAnimationFrame(animate)
      } else {
        handleApprove()
      }
    }
    holdTimer.current = requestAnimationFrame(animate)
  }, [actionDone, actionLoading, handleApprove])

  const onPointerUp = useCallback(() => {
    if (holdTimer.current !== undefined) {
      cancelAnimationFrame(holdTimer.current)
      holdTimer.current = undefined
    }
    setHoldProgress(0)
  }, [])

  const handleDeny = async () => {
    if (actionLoading) return
    setActionLoading(true)
    setActionError('')
    try {
      await gateDeny(token)
      setActionDone('denied')
    } catch {
      setActionError('Gate deny failed. Try again.')
    } finally {
      setActionLoading(false)
    }
  }

  const faceMatchPct = result.face_match_score != null
    ? Math.round(result.face_match_score * 100)
    : null

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden w-full max-w-sm mx-auto">
      {/* Amber top stripe */}
      <div className="h-2 bg-amber-600 rounded-t-xl" />

      <div className="p-5">
        {/* Warning triangle + label */}
        <div className="flex flex-col items-center mb-4">
          <svg
            width="56"
            height="56"
            viewBox="0 0 24 24"
            fill="none"
            aria-label="Flagged — verify identity"
          >
            <path d="M12 2L2 20h20L12 2z" fill="#D97706" />
            <path d="M12 9v5" stroke="white" strokeWidth="2.2" strokeLinecap="round" />
            <circle cx="12" cy="17" r="0.8" fill="white" stroke="white" strokeWidth="1" />
          </svg>
          <p className="text-amber-600 font-extrabold text-xl tracking-widest mt-2">VERIFY IDENTITY</p>
        </div>

        {/* Face comparison */}
        <div className="flex items-center justify-center gap-3 mb-3">
          {/* ID face crop */}
          <div className="flex flex-col items-center">
            <p className="text-xs text-gray-400 mb-1.5 font-medium">ID Photo</p>
            {result.id_face_crop_url ? (
              <img
                src={result.id_face_crop_url}
                alt="ID face crop"
                className="w-20 h-20 rounded-lg object-cover border-2 border-amber-200"
              />
            ) : (
              <div className="w-20 h-20 rounded-lg bg-gray-100 flex items-center justify-center border-2 border-dashed border-gray-300">
                <span className="text-gray-300 text-xs">No ID</span>
              </div>
            )}
          </div>

          {/* Match percentage */}
          <div className="flex flex-col items-center">
            {faceMatchPct !== null ? (
              <>
                <p className="text-lg font-bold text-amber-600">{faceMatchPct}%</p>
                <p className="text-xs text-gray-400">match</p>
              </>
            ) : (
              <p className="text-xs text-gray-400">—</p>
            )}
          </div>

          {/* Live face photo */}
          <div className="flex flex-col items-center">
            <p className="text-xs text-gray-400 mb-1.5 font-medium">Live Photo</p>
            {result.face_photo_url ? (
              <img
                src={result.face_photo_url}
                alt="Live face photo"
                className="w-20 h-20 rounded-lg object-cover border-2 border-amber-200"
              />
            ) : (
              <div className="w-20 h-20 rounded-lg bg-gray-100 flex items-center justify-center border-2 border-dashed border-gray-300">
                <span className="text-gray-300 text-xs">No photo</span>
              </div>
            )}
          </div>
        </div>

        {/* Name and org */}
        <div className="text-center mb-4">
          <p className="text-gray-900 font-bold text-lg">{result.full_name}</p>
          {result.organization && (
            <p className="text-gray-500 text-sm">{result.organization}</p>
          )}
        </div>

        {actionError && (
          <p className="text-red-500 text-xs text-center mb-3 bg-red-50 rounded px-3 py-1.5">
            {actionError}
          </p>
        )}

        {/* Action done confirmation */}
        {actionDone === 'approved' && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 text-center mb-3">
            <p className="text-emerald-700 font-bold text-sm">Entry Approved</p>
          </div>
        )}
        {actionDone === 'denied' && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-center mb-3">
            <p className="text-red-700 font-bold text-sm">Entry Denied</p>
          </div>
        )}

        {/* Gate action buttons */}
        {!actionDone && (
          <div className="flex gap-3 mb-3">
            {/* Approve — tap and hold */}
            <div className="flex-1 relative">
              <button
                onPointerDown={onPointerDown}
                onPointerUp={onPointerUp}
                onPointerLeave={onPointerUp}
                disabled={actionLoading}
                className="relative w-full bg-emerald-600 text-white font-bold rounded-lg py-3 text-sm overflow-hidden select-none touch-none disabled:opacity-60"
                style={{ WebkitUserSelect: 'none' }}
              >
                {/* Progress fill overlay */}
                <span
                  className="absolute inset-0 bg-emerald-800 transition-none rounded-lg origin-left"
                  style={{ transform: `scaleX(${holdProgress})`, transformOrigin: 'left' }}
                />
                <span className="relative z-10">
                  {holdProgress > 0 ? 'Hold...' : 'Hold to Approve'}
                </span>
              </button>
              {holdProgress > 0 && holdProgress < 1 && (
                <p className="text-xs text-gray-400 text-center mt-1">
                  {Math.round(holdProgress * 100)}%
                </p>
              )}
            </div>

            {/* Deny — simple tap */}
            <button
              onClick={handleDeny}
              disabled={actionLoading}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg py-3 text-sm disabled:opacity-60 transition-colors"
            >
              Deny
            </button>
          </div>
        )}

        {/* Scan next */}
        <button
          onClick={onScanNext}
          className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg py-2.5 text-sm transition-colors"
        >
          Scan Next
        </button>
      </div>
    </div>
  )
}
