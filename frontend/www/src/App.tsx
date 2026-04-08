function App() {
  return (
    <div className="min-h-screen bg-navy flex flex-col">
      {/* Hero Image Section */}
      <div className="relative w-full">
        <img
          src="/hero.png"
          alt="Walk for Peace — Buddhist monks walking for peace through the Sri Lankan countryside"
          className="w-full h-auto object-cover"
        />
        {/* Gradient overlay at bottom for smooth transition */}
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-navy to-transparent" />
      </div>

      {/* Content Section */}
      <div className="flex-1 flex flex-col items-center text-center px-4 -mt-8 relative z-10">
        <p className="text-lg md:text-xl text-gray-300 italic mb-6">
          "Today Is My Peaceful Day"
        </p>

        <p className="text-gray-300 max-w-xl text-center mb-10 leading-relaxed">
          A nationwide peaceful walk uniting communities across Sri Lanka.
          Join thousands of people from all backgrounds as we walk together
          to celebrate harmony, reconciliation, and our shared hope for a
          peaceful future.
        </p>

        <a
          href="https://register.walkforpeacelk.org"
          className="inline-flex items-center gap-3 bg-saffron hover:bg-saffron-dark text-white text-lg font-bold rounded-xl px-8 py-4 transition-colors duration-200 mb-4"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          Register as Media Personnel
        </a>

        <p className="text-gray-400 text-sm max-w-md">
          For journalists, photographers, and media professionals covering the event
        </p>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-2xl mx-auto mt-12 mb-6 text-center px-4">
        <p className="text-gray-400 text-sm mb-1">
          Led by Venerable Bhikkhu Paññākāra
        </p>
        <p className="text-gray-500 text-sm mb-4">
          walkforpeacelk.org
        </p>
        <div className="border-t border-gray-700 pt-4">
          <p className="text-gray-500 text-xs">
            &copy; 2026 Walk for Peace Sri Lanka
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
