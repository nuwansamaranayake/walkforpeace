import type { VerifyResponse } from '@walkforpeace/shared'

interface ResultRejectedProps {
  result: VerifyResponse
  onScanNext: () => void
}

function statusLabel(status: string): string {
  switch (status) {
    case 'rejected': return 'REJECTED'
    case 'revoked': return 'REVOKED'
    case 'pending': return 'NOT APPROVED'
    case 'expired': return 'EXPIRED'
    default: return 'INVALID'
  }
}

export default function ResultRejected({ result, onScanNext }: ResultRejectedProps) {
  const label = statusLabel(result.verification_status ?? result.status ?? 'invalid')

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden w-full max-w-sm mx-auto">
      {/* Red top stripe */}
      <div className="h-2 bg-red-600 rounded-t-xl" />

      <div className="p-5">
        {/* X circle + label */}
        <div className="flex flex-col items-center mb-4">
          <svg
            width="56"
            height="56"
            viewBox="0 0 24 24"
            fill="none"
            aria-label="Rejected"
          >
            <circle cx="12" cy="12" r="12" fill="#DC2626" />
            <path
              d="M8 8l8 8M16 8l-8 8"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          </svg>
          <p className="text-red-600 font-extrabold text-2xl tracking-widest mt-2">{label}</p>
        </div>

        {/* Name and org if available */}
        {result.full_name && (
          <div className="text-center mb-3">
            <p className="text-gray-700 font-semibold text-lg">{result.full_name}</p>
            {result.organization && (
              <p className="text-gray-400 text-sm mt-0.5">{result.organization}</p>
            )}
          </div>
        )}

        {/* Do not allow entry */}
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-5 text-center">
          <p className="text-red-700 font-bold text-sm uppercase tracking-wide">Do not allow entry</p>
          {result.message && (
            <p className="text-red-500 text-xs mt-1">{result.message}</p>
          )}
        </div>

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
