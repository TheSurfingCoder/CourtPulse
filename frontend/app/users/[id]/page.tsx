export default function UserProfilePage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1>User Profile: {params.id}</h1>
      <p>This is a dynamic route for user ID: {params.id}</p>
      <p>You can use this ID to fetch user data from your database.</p>
      
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f0f0f0' }}>
        <h3>Route Information:</h3>
        <ul>
          <li><strong>File:</strong> app/users/[id]/page.tsx</li>
          <li><strong>URL Pattern:</strong> /users/[any-id]</li>
          <li><strong>Current ID:</strong> {params.id}</li>
        </ul>
      </div>
    </div>
  )
} 