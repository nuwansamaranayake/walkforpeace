import { Routes, Route, Navigate } from 'react-router-dom'
import PasswordPage from './pages/PasswordPage'
import ScanPage from './pages/ScanPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const session = localStorage.getItem('verify_session')
  if (!session) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PasswordPage />} />
      <Route
        path="/scan"
        element={
          <ProtectedRoute>
            <ScanPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
