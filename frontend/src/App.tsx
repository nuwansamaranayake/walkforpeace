import { Routes, Route } from 'react-router-dom'
import RegisterPage from './pages/RegisterPage'
import StatusPage from './pages/StatusPage'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'
import AdminReview from './pages/AdminReview'
import VerifyPage from './pages/VerifyPage'
import HomePage from './pages/HomePage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/status" element={<StatusPage />} />
      <Route path="/status/:refNumber" element={<StatusPage />} />
      <Route path="/admin" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/review/:id" element={<AdminReview />} />
      <Route path="/verify" element={<VerifyPage />} />
    </Routes>
  )
}
