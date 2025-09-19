'use client';

import { useState, useEffect } from 'react';

interface Court {
  id: number;
  name: string;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export default function CourtsList() {
  const [courts, setCourts] = useState<Court[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCourts();
  }, []);

  const fetchCourts = async () => {
    try {
      setLoading(true);
      // Backend API endpoint
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      
      console.log(JSON.stringify({
        event: 'courts_list_fetch_started',
        timestamp: new Date().toISOString(),
        apiUrl: apiUrl
      }));
      
      const response = await fetch(`${apiUrl}/api/courts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });
      
      console.log(JSON.stringify({
        event: 'courts_list_response_received',
        timestamp: new Date().toISOString(),
        status: response.status,
        ok: response.ok,
        statusText: response.statusText
      }));
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        setCourts(result.data);
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch courts');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Loading courts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', backgroundColor: '#fee', border: '1px solid #fcc', borderRadius: '4px' }}>
        <h3>Error loading courts:</h3>
        <p>{error}</p>
        <button 
          onClick={fetchCourts}
          style={{ padding: '8px 16px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <h2>Available Courts ({courts.length})</h2>
      
      {courts.length === 0 ? (
        <p>No courts found in the database.</p>
      ) : (
        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {courts.map((court) => (
            <div 
              key={court.id} 
              style={{ 
                border: '1px solid #ddd', 
                borderRadius: '8px', 
                padding: '16px',
                backgroundColor: 'white'
              }}
            >
              <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>{court.name}</h3>
              <p style={{ margin: '4px 0', color: '#666' }}>
                <strong>Type:</strong> {court.type}
              </p>
              <p style={{ margin: '4px 0', color: '#666' }}>
                <strong>Surface:</strong> {court.surface}
              </p>
              <p style={{ margin: '4px 0', color: '#666' }}>
                <strong>Public:</strong> {court.is_public ? 'Yes' : 'No'}
              </p>
              <p style={{ margin: '4px 0', color: '#666', fontSize: '12px' }}>
                <strong>Location:</strong> {court.lat.toFixed(6)}, {court.lng.toFixed(6)}
              </p>
            </div>
          ))}
        </div>
      )}
      
      <div style={{ marginTop: '20px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h4>Database Query Info:</h4>
        <p><strong>Endpoint:</strong> GET /api/courts</p>
        <p><strong>Total Courts:</strong> {courts.length}</p>
        <p><strong>Last Updated:</strong> {courts.length > 0 ? new Date(courts[0].updated_at).toLocaleString() : 'N/A'}</p>
      </div>
    </div>
  );
} 