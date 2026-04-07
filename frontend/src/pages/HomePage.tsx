import { Link } from 'react-router-dom'
import { UserPlus, Shield, ScanLine } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-navy text-white">
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <img src="/logo.png" alt="Walk for Peace" className="w-40 h-40 mx-auto mb-6" />
        <h1 className="text-4xl font-bold text-saffron mb-2">Walk for Peace Sri Lanka</h1>
        <p className="text-gold text-lg mb-1">Media Credential Management System</p>
        <p className="text-gray-400 mb-12">April 21, 2026</p>

        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Link to="/register" className="bg-navy-light rounded-xl p-8 hover:ring-2 hover:ring-saffron transition group">
            <UserPlus className="w-12 h-12 text-saffron mx-auto mb-4 group-hover:scale-110 transition" />
            <h2 className="text-xl font-semibold mb-2">Register</h2>
            <p className="text-gray-400 text-sm">Apply for media credentials</p>
          </Link>

          <Link to="/admin" className="bg-navy-light rounded-xl p-8 hover:ring-2 hover:ring-saffron transition group">
            <Shield className="w-12 h-12 text-saffron mx-auto mb-4 group-hover:scale-110 transition" />
            <h2 className="text-xl font-semibold mb-2">Admin</h2>
            <p className="text-gray-400 text-sm">Review & manage applications</p>
          </Link>

          <Link to="/verify" className="bg-navy-light rounded-xl p-8 hover:ring-2 hover:ring-saffron transition group">
            <ScanLine className="w-12 h-12 text-saffron mx-auto mb-4 group-hover:scale-110 transition" />
            <h2 className="text-xl font-semibold mb-2">Verify</h2>
            <p className="text-gray-400 text-sm">Scan QR credentials at event</p>
          </Link>
        </div>

        <p className="text-gray-500 text-xs">Led by Venerable Bhikkhu Paññākāra</p>
      </div>
    </div>
  )
}
