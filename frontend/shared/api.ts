import axios, { type AxiosInstance } from 'axios'
import type {
  RegisterResponse, StatusResponse, RetrieveResponse, OCRResponse,
  VerifyAuthResponse, VerifyResponse, LoginResponse, DashboardStats,
  ApplicationListItem, ApplicationDetail, PaginatedResponse,
  BatchApproveResponse, VerificationLogItem,
} from './types'

function createApi(baseURL = '/api'): AxiosInstance {
  const instance = axios.create({ baseURL })

  instance.interceptors.request.use((config) => {
    // Admin token for admin routes
    const adminToken = localStorage.getItem('admin_token')
    if (adminToken && config.url?.startsWith('/admin')) {
      config.headers.Authorization = `Bearer ${adminToken}`
    }
    // Verify session token for verify routes
    const verifySession = localStorage.getItem('verify_session')
    if (verifySession && config.url?.startsWith('/verify')) {
      config.headers.Authorization = `Bearer ${verifySession}`
    }
    return config
  })

  return instance
}

const api = createApi()

// --- Registration ---
export async function submitRegistration(formData: FormData) {
  const { data } = await api.post<RegisterResponse>('/register', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function checkStatus(refNumber: string) {
  const { data } = await api.get<StatusResponse>(`/register/status/${refNumber}`)
  return data
}

export async function retrieveByPIN(pin: string) {
  const { data } = await api.get<RetrieveResponse>('/register/retrieve', { params: { pin } })
  return data
}

export async function retrieveByIDNumber(idNumber: string) {
  const { data } = await api.get<RetrieveResponse>('/register/retrieve', { params: { id_number: idNumber } })
  return data
}

export async function ocrExtract(file: File) {
  const formData = new FormData()
  formData.append('id_document', file)
  const { data } = await api.post<OCRResponse>('/register/ocr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// --- Verify Auth ---
export async function verifyAuth(password: string) {
  const { data } = await api.post<VerifyAuthResponse>('/verify/auth', { password })
  localStorage.setItem('verify_session', data.session_token)
  return data
}

// --- Verification ---
export async function verifyCredential(token: string) {
  const { data } = await api.get<VerifyResponse>(`/verify/${token}`)
  return data
}

export async function gateApprove(token: string) {
  const { data } = await api.post<{ message: string; badge_number: string }>(`/verify/${token}/gate-approve`)
  return data
}

export async function gateDeny(token: string) {
  const { data } = await api.post<{ message: string; badge_number: string }>(`/verify/${token}/gate-deny`)
  return data
}

// --- Admin ---
export async function adminLogin(username: string, password: string) {
  const { data } = await api.post<LoginResponse>('/admin/login', { username, password })
  localStorage.setItem('admin_token', data.access_token)
  return data
}

export async function getStats() {
  const { data } = await api.get<DashboardStats>('/admin/stats')
  return data
}

export async function getApplications(params: Record<string, any>) {
  const { data } = await api.get<PaginatedResponse<ApplicationListItem>>('/admin/applications', { params })
  return data
}

export async function getApplication(id: string) {
  const { data } = await api.get<ApplicationDetail>(`/admin/applications/${id}`)
  return data
}

export async function reviewApplication(id: string, action: string, notes?: string) {
  const { data } = await api.patch(`/admin/applications/${id}/review`, { action, admin_notes: notes })
  return data
}

export async function revokeCredential(id: string) {
  const { data } = await api.post(`/admin/applications/${id}/revoke`)
  return data
}

export async function batchApprove(applicationIds: string[]) {
  const { data } = await api.post<BatchApproveResponse>('/admin/applications/batch-approve', {
    application_ids: applicationIds,
  })
  return data
}

export async function getVerificationLogs(params: Record<string, any> = {}) {
  const { data } = await api.get<PaginatedResponse<VerificationLogItem>>('/admin/verification-logs', { params })
  return data
}

export async function changePassword(current: string, newPwd: string) {
  const { data } = await api.post('/admin/change-password', { current_password: current, new_password: newPwd })
  return data
}

export { api }
