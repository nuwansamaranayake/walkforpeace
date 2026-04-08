import { Link } from 'react-router-dom'
import { FileText, QrCode, Search } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-navy text-white py-10 text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-saffron tracking-tight">
          Walk for Peace Sri Lanka
        </h1>
        <p className="mt-2 text-gold text-sm md:text-base font-medium tracking-wide">
          2026 — Media Credential Portal
        </p>
        <p className="mt-1 text-white/60 text-xs">register.walkforpeacelk.com</p>
      </header>

      {/* Hero section */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <p className="text-center text-gray-600 max-w-lg mb-10 text-base leading-relaxed">
          Accredited media representatives must register for a credential before covering the Walk
          for Peace. Use this portal to apply or retrieve your QR code.
        </p>

        <div className="grid md:grid-cols-2 gap-6 w-full max-w-2xl">
          {/* Register CTA */}
          <Link
            to="/register"
            className="group flex flex-col items-center bg-navy hover:bg-navy-light text-white rounded-2xl p-8 shadow-lg transition-all duration-200 hover:scale-[1.02] hover:shadow-xl"
          >
            <div className="bg-saffron rounded-full p-4 mb-5 group-hover:bg-saffron-dark transition">
              <FileText className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-xl font-bold mb-2">Register for Media Credential</h2>
            <p className="text-white/70 text-sm text-center">
              New applicants — submit your details, ID document, and face photo to apply for
              accreditation.
            </p>
            <span className="mt-6 inline-block bg-saffron text-white text-sm font-semibold px-6 py-2 rounded-full group-hover:bg-saffron-dark transition">
              Apply Now →
            </span>
          </Link>

          {/* Get QR CTA */}
          <Link
            to="/get-qr"
            className="group flex flex-col items-center bg-white border-2 border-navy hover:border-saffron text-navy rounded-2xl p-8 shadow-lg transition-all duration-200 hover:scale-[1.02] hover:shadow-xl"
          >
            <div className="bg-saffron/10 border-2 border-saffron rounded-full p-4 mb-5 group-hover:bg-saffron group-hover:border-saffron transition">
              <QrCode className="w-8 h-8 text-saffron group-hover:text-white transition" />
            </div>
            <h2 className="text-xl font-bold mb-2">Get Your QR Code</h2>
            <p className="text-gray-600 text-sm text-center">
              Already registered? Retrieve your QR code using your PIN or NIC / Passport number.
            </p>
            <span className="mt-6 inline-block bg-navy text-white text-sm font-semibold px-6 py-2 rounded-full group-hover:bg-saffron transition">
              Retrieve QR →
            </span>
          </Link>
        </div>

        {/* Status link */}
        <div className="mt-8 flex items-center gap-2 text-gray-500 text-sm">
          <Search className="w-4 h-4" />
          <Link to="/status" className="hover:text-saffron underline underline-offset-2 transition">
            Check application status by reference number
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-navy text-white/40 text-center py-4 text-xs">
        Walk for Peace Sri Lanka 2026 &mdash; Media Accreditation System
      </footer>
    </div>
  )
}
