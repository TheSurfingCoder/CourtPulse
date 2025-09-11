import CourtsList from '../components/CourtsList';

export default function Home() {
  return (
    <div>
      <h1>Home Page</h1>
      <p>This is the home page content.</p>
      <p>It&apos;s only wrapped by the root layout, not the users layout.</p>
      <p>Go to <a href="/users">/users</a> to see the nested layout in action!</p>
      
      <hr style={{ margin: '30px 0' }} />
      
      <CourtsList />
    </div>
  )
}