import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Inject auth token for admin routes
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token && config.url?.startsWith('/admin')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 — redirect to login
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname.startsWith('/admin/')) {
      localStorage.removeItem('admin_token')
      window.location.href = '/admin'
    }
    return Promise.reject(err)
  }
)

// --- Registration ---
export async function submitRegistration(formData: FormData) {
  return api.post('/register', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function checkStatus(refNumber: string) {
  return api.get(`/register/status/${refNumber}`)
}

// --- Admin ---
export async function adminLogin(username: string, password: string) {
  const { data } = await api.post('/admin/login', { username, password })
  localStorage.setItem('admin_token', data.access_token)
  return data
}

export async function getApplications(params: Record<string, any>) {
  return api.get('/admin/applications', { params })
}

export async function getApplication(id: string) {
  return api.get(`/admin/applications/${id}`)
}

export async function reviewApplication(id: string, action: string, notes?: string) {
  return api.patch(`/admin/applications/${id}/review`, {
    action,
    admin_notes: notes,
  })
}

export async function revokeCredential(id: string) {
  return api.post(`/admin/applications/${id}/revoke`)
}

export async function getStats() {
  return api.get('/admin/stats')
}

export async function changePassword(current: string, newPwd: string) {
  return api.post('/admin/change-password', {
    current_password: current,
    new_password: newPwd,
  })
}

// --- Verification ---
export async function verifyCredential(token: string) {
  return api.get(`/verify/${token}`)
}

export default api
