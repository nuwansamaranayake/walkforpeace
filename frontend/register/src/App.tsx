import { Routes, Route, Outlet } from 'react-router-dom'
import { AiGNITEFooter } from '@walkforpeace/shared'
import LandingPage from './pages/LandingPage'
import RegisterPage from './pages/RegisterPage'
import GetQRPage from './pages/GetQRPage'
import ConfirmationPage from './pages/ConfirmationPage'
import StatusPage from './pages/StatusPage'

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
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/get-qr" element={<GetQRPage />} />
        <Route path="/confirm" element={<ConfirmationPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/status/:refNumber" element={<StatusPage />} />
      </Route>
    </Routes>
  )
}
