import CourtsList from '../components/CourtsList';
import CourtsMap from '../components/CourtsMap';

export default function Home() {
  return (
    <div>
      <p>Find and explore sports courts in your area.</p>
      <p>Go to <a href="/users">/users</a> to see the nested layout in action!</p>
      
      <hr style={{ margin: '30px 0' }} />
      
      {/* Interactive Map */}
      <div style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', color: '#333' }}>Interactive Courts Map</h2>
        <CourtsMap className="rounded-lg shadow-lg" />
      </div>
      
      <hr style={{ margin: '30px 0' }} />
      
      {/* Courts List */}
      <div>
        <h2 style={{ marginBottom: '20px', color: '#333' }}>All Courts</h2>
        <CourtsList />
      </div>
    </div>
  )
}