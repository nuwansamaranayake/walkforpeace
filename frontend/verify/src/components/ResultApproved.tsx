import type { VerifyResponse } from '@walkforpeace/shared'

interface ResultApprovedProps {
  result: VerifyResponse
  onScanNext: () => void
}

export default function ResultApproved({ result, onScanNext }: ResultApprovedProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden w-full max-w-sm mx-auto">
      {/* Green top stripe */}
      <div className="h-2 bg-emerald-600 rounded-t-xl" />

      <div className="p-5">
        {/* Checkmark + VERIFIED */}
        <div className="flex flex-col items-center mb-4">
          <svg
            width="56"
            height="56"
            viewBox="0 0 24 24"
            fill="none"
            aria-label="Verified"
          >
            <circle cx="12" cy="12" r="12" fill="#059669" />
            <path
              d="M7 12.5l3.5 3.5 6.5-7"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-emerald-600 font-extrabold text-2xl tracking-widest mt-2">VERIFIED</p>
        </div>

        {/* Face photo */}
        {result.face_photo_url && (
          <div className="flex justify-center mb-4">
            <img
              src={result.face_photo_url}
              alt={result.full_name ?? 'Credential holder'}
              className="w-24 h-24 rounded-full object-cover border-4 border-emerald-100 shadow"
            />
          </div>
        )}

        {/* Name and org */}
        <div className="text-center mb-3">
          <p className="text-gray-900 font-bold text-xl leading-tight">{result.full_name}</p>
          {result.organization && (
            <p className="text-gray-500 text-sm mt-0.5">{result.organization}</p>
          )}
          {result.designation && (
            <p className="text-gray-400 text-xs mt-0.5">{result.designation}</p>
          )}
        </div>

        {/* Badge number */}
        {result.badge_number && (
          <div className="flex justify-center mb-5">
            <span className="bg-emerald-50 border border-emerald-200 text-emerald-700 font-mono font-bold text-sm px-4 py-1.5 rounded-lg tracking-wider">
              {result.badge_number}
            </span>
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
