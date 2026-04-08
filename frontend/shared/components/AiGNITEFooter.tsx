export function AiGNITEFooter() {
  return (
    <div className="w-full text-center py-3 mt-auto">
      <p style={{ fontSize: '11px', color: '#9ca3af', letterSpacing: '0.02em' }}>
        Developed by{' '}
        <a
          href="https://aignitek.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#9ca3af', textDecoration: 'underline', textUnderlineOffset: '2px' }}
        >
          AiGNITE
        </a>{' '}
        Software Pvt. Ltd.{' '}
        <span style={{ margin: '0 4px', opacity: 0.5 }}>&bull;</span>{' '}
        <a
          href="https://aignitek.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#9ca3af', textDecoration: 'none' }}
        >
          aignitek.com
        </a>
      </p>
    </div>
  )
}
