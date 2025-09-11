export default function UsersPage() {
  return (
    <div>
      <h1>Users Page</h1>
      <p>This is the users page content.</p>
      <p>Notice how it&apos;s wrapped by the users layout above!</p>
      
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#e8f5e8' }}>
        <h3>Test Dynamic Routes:</h3>
        <ul>
          <li><a href="/users/123">/users/123</a> - User with ID 123</li>
          <li><a href="/users/john-doe">/users/john-doe</a> - User with slug &quot;john-doe&quot;</li>
          <li><a href="/users/abc-xyz">/users/abc-xyz</a> - User with slug &quot;abc-xyz&quot;</li>
        </ul>
        <p><small>Try changing the URL to see different user IDs!</small></p>
      </div>
    </div>
  )
}