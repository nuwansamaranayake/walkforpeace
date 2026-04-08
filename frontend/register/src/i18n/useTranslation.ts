import { useState, useCallback } from 'react'
import translations from './translations.json'

type Lang = 'en' | 'si'

export function useTranslation() {
  const [lang, setLang] = useState<Lang>(
    () => (localStorage.getItem('lang') as Lang) || 'en'
  )

  const t = useCallback(
    (key: string): string => {
      const dict = translations[lang] as Record<string, string>
      return dict[key] || (translations.en as Record<string, string>)[key] || key
    },
    [lang]
  )

  const toggleLang = useCallback(() => {
    setLang((prev) => {
      const next = prev === 'en' ? 'si' : 'en'
      localStorage.setItem('lang', next)
      return next
    })
  }, [])

  return { t, lang, toggleLang }
}
