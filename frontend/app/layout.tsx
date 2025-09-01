export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div style={{ border: '3px solid blue', padding: '10px', margin: '10px' }}>
          <h1 style={{ color: 'blue' }}>ROOT LAYOUT</h1>
          <p style={{ color: 'blue' }}>This blue border is from the root layout - it wraps everything below!</p>
          {children}
        </div>
      </body>
    </html>
  )
}