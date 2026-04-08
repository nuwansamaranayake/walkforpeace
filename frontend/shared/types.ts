// Application status enum
export type ApplicationStatus = 'pending_review' | 'approved' | 'rejected' | 'revoked'
export type VerificationStatus = 'pending' | 'approved' | 'flagged' | 'rejected' | 'revoked'
export type MediaType = 'print' | 'tv' | 'radio' | 'online' | 'photographer' | 'freelance'

// Registration
export interface RegisterResponse {
  ref_number: string
  pin_code: string
  message: string
  status: ApplicationStatus
  qr_code_url: string
}

export interface StatusResponse {
  ref_number: string
  full_name: string
  organization: string
  status: ApplicationStatus
  credential?: CredentialInfo
}

export interface RetrieveResponse {
  ref_number: string
  pin_code: string
  full_name: string
  organization: string
  status: ApplicationStatus
  verification_status: VerificationStatus
  qr_code_url: string | null
  badge_pdf_url: string | null
  badge_number: string
  message: string
}

// Verification
export interface VerifyAuthResponse {
  session_token: string
  expires_at: string
}

export interface VerifyResponse {
  valid: boolean
  status: string
  verification_status?: VerificationStatus
  full_name?: string
  organization?: string
  designation?: string
  media_type?: string
  face_photo_url?: string
  id_face_crop_url?: string | null
  face_match_score?: number | null
  badge_number?: string
  can_gate_approve?: boolean | null
  message: string
}

// Admin
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  must_change_password: boolean
}

export interface BackupStatus {
  last_backup_at: string | null
  last_backup_size: number | null
  last_backup_size_hr: string | null
  last_backup_key: string | null
  total_backups: number
  status: string
}

export interface DashboardStats {
  total_registered: number
  pending: number
  approved: number
  rejected: number
  flagged: number
  total_scans_today: number
  active_gatekeepers: number
  backup: BackupStatus | null
}

export interface ApplicationListItem {
  id: string
  ref_number: string
  full_name: string
  organization: string
  designation: string
  email: string
  media_type: MediaType
  status: ApplicationStatus
  face_match_score: number | null
  face_match_flagged: boolean
  pin_code: string | null
  id_number: string | null
  created_at: string
}

export interface CredentialInfo {
  id: string
  credential_token: string
  qr_code_url: string | null
  badge_pdf_url: string | null
  badge_number: string
  issued_at: string
  expires_at: string
  is_revoked: boolean
  verification_status: VerificationStatus
}

export interface ApplicationDetail {
  id: string
  ref_number: string
  full_name: string
  organization: string
  designation: string
  email: string
  media_type: MediaType
  status: ApplicationStatus
  face_match_score: number | null
  face_match_flagged: boolean
  pin_code: string | null
  id_number: string | null
  created_at: string
  phone: string
  country: string
  id_document_url: string
  id_face_crop_url: string | null
  face_photo_url: string
  id_type: string | null
  ocr_extracted_name: string | null
  ocr_extracted_id: string | null
  admin_notes: string | null
  reviewed_at: string | null
  reviewed_by: string | null
  updated_at: string
  credential: CredentialInfo | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface BatchApproveRequest {
  application_ids: string[]
}

export interface BatchApproveResponse {
  approved_count: number
  message: string
}

export interface VerificationLogItem {
  id: string
  credential_id: string
  badge_number: string
  full_name: string
  scanned_at: string
  scanned_by_ip: string
  result: string
  verified_by_action: string | null
}

// Scan log for per-application scan history (Task 2)
export interface ScanLogItem {
  id: string
  scanned_at: string
  scanned_by_ip: string | null
  result: string
  verified_by_action: string | null
  latitude: number | null
  longitude: number | null
  place_name: string | null
  device_id: string | null
}

// Global scan activity (dashboard tab)
export interface ScanActivityItem {
  id: string
  scanned_at: string
  full_name: string
  badge_number: string | null
  result: string
  verified_by_action: string | null
  place_name: string | null
  device_id: string | null
  scanned_by_ip: string | null
}

// Gatekeeper info (Task 4)
export interface GatekeeperInfo {
  id: string
  device_name: string | null
  device_ip: string | null
  screen_size: string | null
  total_scans: number
  last_scan_at: string | null
  last_location: string | null
  created_at: string
  status: 'active' | 'inactive'
}
