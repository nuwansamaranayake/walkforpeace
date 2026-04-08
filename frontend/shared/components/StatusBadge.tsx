import React from 'react'
import type { VerificationStatus } from '../types'

const statusConfig: Record<VerificationStatus, { label: string; bg: string; text: string }> = {
  approved: { label: 'Approved', bg: 'bg-green-100', text: 'text-green-800' },
  flagged: { label: 'Flagged', bg: 'bg-amber-100', text: 'text-amber-800' },
  rejected: { label: 'Rejected', bg: 'bg-red-100', text: 'text-red-800' },
  revoked: { label: 'Revoked', bg: 'bg-red-100', text: 'text-red-800' },
  pending: { label: 'Pending', bg: 'bg-gray-100', text: 'text-gray-800' },
}

interface Props {
  status: VerificationStatus
  className?: string
}

export function StatusBadge({ status, className = '' }: Props) {
  const config = statusConfig[status] || statusConfig.pending
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text} ${className}`}>
      {config.label}
    </span>
  )
}
