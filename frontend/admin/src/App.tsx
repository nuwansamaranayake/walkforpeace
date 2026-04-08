import { Navigate, Route, Routes, Outlet } from 'react-router-dom'
import { AiGNITEFooter } from '@walkforpeace/shared'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ReviewPage from './pages/ReviewPage'
import LogsPage from './pages/LogsPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('admin_token')
  if (!token) return <Navigate to="/" replace />
  return <>{children}</>
}

function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1">
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
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/review/:id" element={<RequireAuth><ReviewPage /></RequireAuth>} />
        <Route path="/logs" element={<RequireAuth><LogsPage /></RequireAuth>} />
      </Route>
    </Routes>
  )
}
