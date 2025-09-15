import '../styles/globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
          <header style={{ marginBottom: '30px', borderBottom: '2px solid #e5e7eb', paddingBottom: '20px' }}>
            <h1 style={{ color: '#1f2937', fontSize: '2rem', margin: '0', fontWeight: 'bold' }}>🏟️ CourtPulse</h1>
            <p style={{ color: '#6b7280', margin: '8px 0 0 0' }}>Discover and explore sports courts near you</p>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}