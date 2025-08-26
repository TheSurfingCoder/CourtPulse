export default function UsersLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div>
      <h2>Users Layout</h2>
      <p>This is the users layout wrapping the page below:</p>
      <hr />
      {children}
    </div>
  )
} 