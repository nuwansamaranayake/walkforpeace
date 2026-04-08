import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import RegisterPage from './pages/RegisterPage'
import GetQRPage from './pages/GetQRPage'
import ConfirmationPage from './pages/ConfirmationPage'
import StatusPage from './pages/StatusPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/get-qr" element={<GetQRPage />} />
      <Route path="/confirm" element={<ConfirmationPage />} />
      <Route path="/status" element={<StatusPage />} />
      <Route path="/status/:refNumber" element={<StatusPage />} />
    </Routes>
  )
}
