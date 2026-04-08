import React from 'react'

interface Props {
  language: string
  onToggle: (lang: string) => void
  languages?: { code: string; label: string }[]
}

const defaultLanguages = [
  { code: 'en', label: 'EN' },
  { code: 'si', label: 'සිං' },
  { code: 'ta', label: 'தமிழ்' },
]

export function LanguageToggle({ language, onToggle, languages = defaultLanguages }: Props) {
  return (
    <div className="flex gap-1">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => onToggle(lang.code)}
          className={`px-2 py-1 text-xs rounded ${
            language === lang.code
              ? 'bg-white text-[#1B2A4A] font-bold'
              : 'text-white/80 hover:text-white'
          }`}
        >
          {lang.label}
        </button>
      ))}
    </div>
  )
}
