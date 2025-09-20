import CourtsMap from '../components/CourtsMap';

export default function Home() {
  return (
    <div>
      <h1>CourtPulse</h1>
      <p>Find and explore sports courts in your area.</p>
      <p>It&apos;s only wrapped by the root layout, not the users layout.</p>
      <p>Go to <a href="/users">/users</a> to see the nested layout in action!</p>
      
      <hr style={{ margin: '30px 0' }} />
      
      {/* Interactive Map */}
      <div style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', color: '#333' }}>Interactive Courts Map</h2>
        <CourtsMap className="rounded-lg shadow-lg" />
      </div>
      
    </div>
  )
}