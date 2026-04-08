import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AiGNITEFooter } from '@walkforpeace/shared'
import PasswordPage from './pages/PasswordPage'
import ScanPage from './pages/ScanPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const session = localStorage.getItem('verify_session')
  if (!session) return <Navigate to="/" replace />
  return <>{children}</>
}

function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 flex flex-col">
        <Outlet />
      </div>
      <AiGNITEFooter />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
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
      </Route>
    </Routes>
  )
}
